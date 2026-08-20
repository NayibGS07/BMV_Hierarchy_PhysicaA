# --- Notebook code cell 8 ---

@dataclass
class RNGPack:
    mc: np.random.Generator
    boot: np.random.Generator
    misc: np.random.Generator
    _ss: np.random.SeedSequence = field(repr=False)

def make_rngs(seed: int) -> RNGPack:
    ss = np.random.SeedSequence(seed)
    c = ss.spawn(3)
    return RNGPack(mc=np.random.default_rng(c[0]),
                   boot=np.random.default_rng(c[1]),
                   misc=np.random.default_rng(c[2]), _ss=ss)

def derive_rng(rngs: RNGPack, *keys: Any) -> np.random.Generator:
    key_str = "_".join(str(k) for k in keys)
    digest = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
    key_int = int(digest, 16) % (2**31)
    ss = np.random.SeedSequence([int(rngs._ss.entropy), key_int])
    return np.random.default_rng(ss)
