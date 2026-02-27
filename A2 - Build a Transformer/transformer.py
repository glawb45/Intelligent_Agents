"""
Building a Transformer from Scratch with Numpy

- Scaled Dot-Product Attention
- Multi-Head Attention
- Position-wise Feed-Forward Network
- Positional Encoding
- Layer Normalization
- Encoder Layer
- Decoder Layer
- Full Transformer (Encoder + Decoder + output)

# Attribution: Outline help from Claude (not code, but help in detailed transformer structure)

"""

import numpy as np

# Activation Functions


def softmax(x, axis=1):
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)


def relu(x):
    return np.maximum(0, x)


# Layer Normalization


class LayerNorm:
    """
    Layer Normalization: Normalize of last dimension
    Params: gamma (scale), beta (shift)
    """

    def __init__(self, d_model, eps=1e-6):
        # Set class parameters
        self.gamma = np.ones(d_model)
        self.beta = np.zeros(d_model)
        self.eps = eps

    def forward(self, x):
        # Normalize scale and shift
        mean = x.mean(axis=1, keepdims=True)
        std = x.std(axis=1, keepdims=True)
        return self.gamma * (x - mean) / (std + self.eps) + self.beta


# Positional Encoding


class PositionalEncoding:
    """
    Sinusoidal positional encoding added to token embeddings
    PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
    PE(pos, 2i +1) = cos(pos / 10000^(2i/d_model))
    """

    def __init__(self, d_model, max_len=5000):
        pe = np.zeros((max_len, d_model))
        pos = np.arange(max_len)[:, None]
        div = np.exp(
            np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model)
        )  # (d_model / 2)

        pe[:, 0::2] = np.sin(pos * div)
        pe[:, 1::2] = np.cos(pos * div)
        self.pe = pe[None, :, :]  # project over batch

    def forward(self, x):
        return x + self.pe[:, : x.shape[1], :]


# Scaled Dot-Product Attention


def scaled_dot_product_attention(Q, K, V, mask=None):
    d_k = Q.shape[-1]
    # Compute raw attention scores
    raw_attn = Q @ K.swapaxes(-1, -2) / np.sqrt(d_k)

    # Apply the mask
    if mask is not None:
        raw_attn = np.where(mask, -1e9, raw_attn)

    # Softmax
    weights = softmax(raw_attn, axis=-1)

    # Multiply by value vectors
    output = weights @ V

    return output, weights


# Multi-Head Attention


class MultiHeadAttention:
    """
    Multi-head attention with h heads.
    Projects Q, K, V h times into subspaces,
    runs attention in parallel, then concatenates and projects.
    """

    def __init__(self, d_model, n_heads):
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"
        self.h = n_heads
        self.d_k = d_model // n_heads
        self.d_model = d_model

        # Weight matrices - initialize with small random values
        scale = np.sqrt(2.0 / (d_model + self.d_k))
        self.W_Q = np.random.randn(d_model, d_model) * scale
        self.W_K = np.random.randn(d_model, d_model) * scale
        self.W_V = np.random.randn(d_model, d_model) * scale
        self.W_O = np.random.randn(d_model, d_model) * scale

    def _split_heads(self, x):
        batch, seq, _ = x.shape
        x = x.reshape(batch, seq, self.h, self.d_k)

        return x.transpose(0, 2, 1, 3)

    def _merge_heads(self, x):
        batch, _, seq, _ = x.shape
        x = x.transpose(0, 2, 1, 3)

        return x.reshape(batch, seq, self.d_model)

    def forward(self, Q, K, V, mask=None):
        # Linear projections by batch
        Q_ = self._split_heads(Q @ self.W_Q)
        K_ = self._split_heads(K @ self.W_K)
        V_ = self._split_heads(V @ self.W_V)

        # Attention (project over batch and heads)
        attn_out, self.attn_weights = scaled_dot_product_attention(Q_, K_, V_, mask)

        # Merge heads and final linear
        concat = self._merge_heads(attn_out)

        return concat @ self.W_O


# Position-wise FFNN


class FFNN:
    """
    Two-layer fully-connected network applied position-wise
    """

    def __init__(self, d_model, d_ff):
        scale1 = np.sqrt(2.0 / (d_model + d_ff))
        self.W_1 = np.random.randn(d_model, d_ff) * scale1
        self.b_1 = np.zeros(d_ff)

        scale2 = np.sqrt(2.0 / (d_model + d_ff))
        self.W_2 = np.random.randn(d_ff, d_model) * scale2
        self.b_2 = np.zeros(d_model)

    def forward(self, x):
        relu_1 = relu(x @ self.W_1 + self.b_1)
        return relu_1 @ self.W_2 + self.b_2


# Encoder Layer


class EncoderLayer:
    """
    Single Transformer encoder layer:
        Input x --> Multi-Head Self-Attention --> Add + Norm
                --> FFNN                      --> Add + Norm
    """

    def __init__(self, d_model, n_heads, d_ff):
        self.self_attn = MultiHeadAttention(d_model, n_heads)
        self.ff = FFNN(d_model, d_ff)
        self.norm1 = LayerNorm(d_model)
        self.norm2 = LayerNorm(d_model)

    def forward(self, x, src_mask=None):
        """
        src_mask: Optional padding mask (batch, 1, 1, src_len)
        """

        # Self-attention sub-layer
        attn_out = self.self_attn.forward(x, x, x, mask=src_mask)
        x = self.norm1.forward(x + attn_out)  # residual + norm

        # Feed-forward sub-layer
        ff_out = self.ff.forward(x)
        x = self.norm2.forward(x + ff_out)

        return x


# Decoder Layer


class DecoderLayer:
    """
    Single Transformer decoder layer:
        Input x --> Masked Multi-Head Self-Attention --> Add + Norm
                --> Multi-Head Cross-Attention       --> Add + Norm
                --> Feed-Forward                     --> Add + Norm
    """

    def __init__(self, d_model, n_heads, d_ff):
        self.self_attn = MultiHeadAttention(d_model, n_heads)
        self.cross_attn = MultiHeadAttention(d_model, n_heads)
        self.ff = FFNN(d_model, d_ff)
        self.norm1 = LayerNorm(d_model)
        self.norm2 = LayerNorm(d_model)
        self.norm3 = LayerNorm(d_model)

    def forward(self, x, enc_output, src_mask=None, tgt_mask=None):
        """
        tgt_mask: causal + padding mask (batch, 1, tgt_len, tgt_len)
        """

        # Masked self-attention
        attn_out = self.self_attn.forward(x, x, x, mask=tgt_mask)
        x = self.norm1.forward(x + attn_out)

        # Cross attention over encoder output
        cross_attn_out = self.cross_attn.forward(
            x, enc_output, enc_output, mask=src_mask
        )
        x = self.norm2.forward(x + cross_attn_out)

        # Feed-forward
        ff_out = self.ff.forward(x)
        x = self.norm3.forward(x + ff_out)

        return x


# Encoder Stack


class EncoderStack:
    """
    1. Embed input tokens
    2. Add positional encoding
    3. Stack n encoder layers --> passed into every cross-attention layer in decoder
    """

    def __init__(self, d_model, n_heads, d_ff, n_layers):
        self.layers = [EncoderLayer(d_model, n_heads, d_ff) for _ in range(n_layers)]
        self.norm = LayerNorm(d_model)

    def forward(self, x, src_mask=None):
        for layer in self.layers:
            x = layer.forward(x, src_mask)

        return self.norm.forward(x)


# Decoder Stack


class DecoderStack:
    """
    1. Embed target tokens
    2. Add positional encoding
    3. Build causal mask
    4. Stack n decoder layers
    """

    def __init__(self, d_model, n_heads, d_ff, n_layers):
        self.layers = [DecoderLayer(d_model, n_heads, d_ff) for _ in range(n_layers)]
        self.norm = LayerNorm(d_model)

    def forward(self, x, enc_output, src_mask=None, tgt_mask=None):
        for layer in self.layers:
            x = layer.forward(x, enc_output, src_mask, tgt_mask)

        return self.norm.forward(x)


# Masks


def make_padding_mask(seq, pad_idx=0):
    """
    Creates padding mask for token index sequence.
    True where token == pad_idx.
    """
    return (seq == pad_idx)[:, None, None, :]  # broadcast over heads and query position


def make_lookahead_mask(seq_len):
    """
    Upper-triangular lookahead mask.
    Pos (i, j) is masked when j > i (True).
    """

    mask = np.triu(
        np.ones((seq_len, seq_len), dtype=bool), k=1
    )  # np.triu extracts upper-triangular matrix
    return mask[None, None, :, :]  # (1, 1, seq_len, seq_len)


def make_tgt_mask(tgt, pad_idx=0):
    """
    Combined target mask = (lookahead mask or padding mask).
    """

    pad_mask = make_padding_mask(tgt, pad_idx)  # (batch, 1, 1, tgt_len)
    lookahead_mask = make_lookahead_mask(tgt.shape[1])  # (1, 1, tgt_len, tgt_len)

    return pad_mask | lookahead_mask  # broadcast => (batch, 1, tgt_len, tgt_len)


# Full Transformer


class Transformer:
    """
    Full encoder-decoder transformer implementation.

    Arguments:
        src_vocab_size: size of source vocabulary
        tgt_vocab_size: size of target vocabulary
        d_model: embedding / model dimension (default: 512)
        n_heads: number of attention heads (default: 8)
        d_ff: inner feed-forward dimension (default: 2048)
        n_layers: number of encoder and decoder layers (default: 6)
        max_len: maximum sequence length (default: 5000)
        pad_idx: padding token index (default: 0)
    """

    def __init__(
        self,
        src_vocab_size,
        tgt_vocab_size,
        d_model=512,
        n_heads=8,
        d_ff=2048,
        n_layers=6,
        max_len=5000,
        pad_idx=0,
    ):

        self.pad_idx = pad_idx
        self.d_model = d_model

        # Embeddings (look-up tables)
        scale = np.sqrt(d_model)
        self.src_embed = np.random.randn(src_vocab_size, d_model) / scale
        self.tgt_embed = np.random.randn(tgt_vocab_size, d_model) / scale

        # Positional encoding
        self.pos_enc = PositionalEncoding(d_model, max_len)

        # Encoder, Decoder Layers
        self.encoder = EncoderStack(d_model, n_heads, d_ff, n_layers)
        self.decoder = DecoderStack(d_model, n_heads, d_ff, n_layers)

        # Ouput matrix: Final linear projections to vocabulary logits
        self.output_proj = np.random.randn(d_model, tgt_vocab_size) / np.sqrt(d_model)

    def encode(self, src):
        """
        Embed + positionally encode source
        Buid source padding mask
        Run encoder stack
        Embed + positionally encode target
        """

        src_mask = make_padding_mask(src, self.pad_idx)
        x = self.src_embed[src] * np.sqrt(self.d_model)  # embedding + scale
        x = self.pos_enc.forward(x)

        return self.encoder.forward(x, src_mask), src_mask

    def decode(self, tgt, enc_output, src_mask):
        """
        Build causal mask for decoder
        Run decoder stack, pass in encoder output to every layer (cross-attention layers)
        """

        tgt_mask = make_tgt_mask(tgt, self.pad_idx)
        x = self.tgt_embed[tgt] * np.sqrt(self.d_model)
        x = self.pos_enc.forward(x)

        return self.decoder.forward(x, enc_output, src_mask, tgt_mask)

    def forward(self, src, tgt):
        """
        Apply final linear projection
        Return logits and softmax probabilities
        """

        enc_output, src_mask = self.encode(src)
        dec_output = self.decode(tgt, enc_output, src_mask)
        logits = dec_output @ self.output_proj

        return logits


# Testing

if __name__ == "__main__":
    np.random.seed(123)

    # Run a tiny model to verify shapes
    SRC_VOCAB = 200
    TGT_VOCAB = 180
    BATCH = 2
    SRC_LEN = 10
    TGT_LEN = 8

    model = Transformer(
        src_vocab_size=SRC_VOCAB,
        tgt_vocab_size=TGT_VOCAB,
        d_model=64,
        n_heads=4,
        d_ff=128,
        n_layers=2,
        max_len=100,
        pad_idx=0,
    )

    # Random integer sequences (0 = padding)
    src = np.random.randint(1, SRC_VOCAB, (BATCH, SRC_LEN))
    tgt = np.random.randint(1, TGT_VOCAB, (BATCH, TGT_LEN))

    logits = model.forward(src, tgt)

    print("Forward pass successful")
    print(f"src shape: {src.shape}")
    print(f"tgt shape: {tgt.shape}")
    print(f"logits shape: {logits.shape}")  # expected (2, 8, 180)

    assert logits.shape == (BATCH, TGT_LEN, TGT_VOCAB), "Error: shape mismatch"
    print("All shape assertions passed")
