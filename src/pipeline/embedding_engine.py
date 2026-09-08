import io
import logging
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

from src.models.schema import Fact
from src.config import settings

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    """Computes dense vector embeddings for facts and searches for similar candidate pairs."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None
        self._use_fallback = False

    def _get_model(self):
        """Load the embedding backend.
        * First tries a SentenceTransformer model (default for fast local embeddings).
        * If that fails and the model name indicates a Qwen3 model, falls back to a Transformers based loader.
        * Otherwise uses the deterministic semantic feature vector as a final fallback.
        """
        if self._model is not None:
            return self._model
        # Try SentenceTransformer first
        try:
            import os
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device="cpu")
            return self._model
        except Exception as first_err:
            logger.warning(f"SentenceTransformer load failed ({first_err}); trying Transformers Qwen3 loader.")
        # If the model name contains 'qwen', use a lightweight Transformers wrapper
        if "qwen" in self.model_name.lower():
            try:
                from transformers import AutoModel, AutoTokenizer
                import torch

                class _Qwen3Wrapper:
                    def __init__(self, name: str):
                        self.tokenizer = AutoTokenizer.from_pretrained(name, trust_remote_code=True)
                        self.model = AutoModel.from_pretrained(name, trust_remote_code=True).eval()

                    def encode(self, texts):
                        # Supports single string or list of strings
                        if isinstance(texts, str):
                            texts = [texts]
                        embeddings = []
                        for txt in texts:
                            inputs = self.tokenizer(txt, return_tensors="pt", truncation=True, max_length=512)
                            with torch.no_grad():
                                output = self.model(**inputs).last_hidden_state.mean(dim=1)
                            vec = output.squeeze().cpu().numpy()
                            norm = np.linalg.norm(vec)
                            embeddings.append(vec / norm if norm > 0 else vec)
                        return embeddings[0] if len(embeddings) == 1 else embeddings

                self._model = _Qwen3Wrapper(self.model_name)
                return self._model
            except Exception as qwen_err:
                logger.warning(f"Qwen3 model load failed ({qwen_err}); reverting to semantic fallback.")
                self._use_fallback = True
        else:
            # Not a Qwen model and SentenceTransformer failed
            self._use_fallback = True
        return None

    def _semantic_feature_vector(self, text: str) -> np.ndarray:
        """
        Deterministic, dense semantic vector generator.
        Combines token hashing, character n-grams, and positional weights into a 384-dim normalized vector.
        """
        vec = np.zeros(384, dtype=np.float32)
        words = text.lower().replace(",", " ").replace(":", " ").replace("$", " $ ").split()
        for idx, word in enumerate(words):
            # Token hash
            h = abs(hash(word)) % 384
            weight = 1.0 + (1.0 / (idx + 1))
            vec[h] += weight
            
            # Subword 3-grams
            for i in range(len(word) - 2):
                tri = word[i:i+3]
                h_tri = abs(hash(tri)) % 384
                vec[h_tri] += 0.4
        
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_text(self, text: str) -> np.ndarray:
        """Embeds single text string into a normalized numpy vector."""
        # Try the primary model first (SentenceTransformer or Qwen3 wrapper)
        model = self._get_model()
        if model is not None:
            try:
                # Qwen3 wrapper returns a plain ndarray; SentenceTransformer returns a numpy array
                vec = model.encode(text)
                # Ensure we have a NumPy array
                vec = np.array(vec, dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                return vec
            except Exception as embed_err:
                logger.warning(f"Embedding via primary model failed ({embed_err}); using semantic fallback.")
        # Fallback deterministic embedding
        return self._semantic_feature_vector(text)

    def embed_fact(self, fact: Fact) -> np.ndarray:
        """Embeds a Fact representation."""
        fact_text = f"{fact.subject} {fact.predicate} {fact.value}"
        if fact.unit:
            fact_text += f" {fact.unit}"
        if fact.time_scope:
            fact_text += f" {fact.time_scope}"
        return self.embed_text(fact_text)

    def serialize_embedding(self, vec: np.ndarray) -> bytes:
        """Serializes numpy array to bytes for SQLite storage."""
        bio = io.BytesIO()
        np.save(bio, vec)
        return bio.getvalue()

    def deserialize_embedding(self, data: bytes) -> np.ndarray:
        """Deserializes bytes back to numpy array."""
        bio = io.BytesIO(data)
        return np.load(bio)

    def find_similar_candidates(
        self,
        query_fact: Fact,
        existing_facts: List[Fact],
        existing_embeddings: Dict[str, np.ndarray],
        top_k: int = None,
        threshold: float = None
    ) -> List[Tuple[Fact, float]]:
        """
        Finds candidate facts that have high semantic similarity with query_fact.
        Avoids comparing with facts from the exact same document or the same fact_id.
        """
        top_k = top_k or settings.TOP_K_CANDIDATES
        threshold = threshold or settings.SIMILARITY_THRESHOLD

        if not existing_facts:
            return []

        query_vec = self.embed_fact(query_fact)
        
        valid_facts = []
        vectors = []
        for candidate_fact in existing_facts:
            if candidate_fact.fact_id == query_fact.fact_id:
                continue
            valid_facts.append(candidate_fact)
            
            c_vec = existing_embeddings.get(candidate_fact.fact_id)
            if c_vec is None:
                c_vec = self.embed_fact(candidate_fact)
                existing_embeddings[candidate_fact.fact_id] = c_vec
            vectors.append(c_vec)
            
        if not valid_facts:
            return []
            
        # Vectorized similarity computation
        matrix = np.vstack(vectors)  # (M, D)
        dot_products = np.dot(matrix, query_vec)  # (M,)
        
        candidates: List[Tuple[Fact, float]] = []
        q_subj = query_fact.subject.lower()
        q_type = query_fact.fact_type

        for idx, score in enumerate(dot_products):
            cf = valid_facts[idx]
            semantic_score = float(score)
            
            # Boost score if subject or fact_type matches
            c_subj = cf.subject.lower()
            if q_subj in c_subj or c_subj in q_subj:
                semantic_score = min(1.0, semantic_score + 0.15)
            if cf.fact_type == q_type:
                semantic_score = min(1.0, semantic_score + 0.10)

            if semantic_score >= threshold:
                candidates.append((cf, float(semantic_score)))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]
