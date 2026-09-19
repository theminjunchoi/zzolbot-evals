"""생성 엔진. MLX와 PyTorch를 같은 인터페이스 뒤에 둔다.

**이름 주의.** 여기서 엔진은 모델을 돌리는 연산 프레임워크다. 팀 레포의 `backend/`가
Spring 서버라 backend로 부르면 헷갈린다. 그래서 engine이다.

**왜 나누는가.** 지금까지 학습과 추론 경로가 MLX 하나였다. 그러면 측정한 수치가 방법의
결과인지 프레임워크의 결과인지 구별할 수 없다. 이 레포의 반복 실패 2번(정의 불일치)이
정확히 이 형태이고, 처방은 "새 도구가 기존 수치를 재현하는지 대조한다"이다.

**대조가 성립하려면 엔진 바깥이 완전히 같아야 한다.** 프롬프트 조립, JSON 추출, 채점,
접지 판정이 한 벌만 있어야 불일치가 나왔을 때 엔진으로 좁혀진다. 그래서 이 인터페이스는
**토큰을 만드는 일만** 맡고 나머지는 호출부에 그대로 둔다.

주의. 두 엔진의 수치가 완전히 일치할 것을 기대하면 안 된다. 부동소수점 누적 순서가
달라 로짓 하위 자리가 갈리고, 그리디에서 argmax 타이 근처 토큰이 뒤집힌다. 판정 기준은
"같은 엔진을 시드만 바꿔 두 번 잰 불일치" 이하인지로 잡는다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from harness.constrained import CitationConstraint


class GenerationEngine(ABC):
    """system과 user를 받아 원문 텍스트를 돌려주는 포트.

    JSON 추출과 채점은 호출부가 한다. 백엔드는 생성만 책임진다.
    """

    #: 실제로 올라간 가중치의 정밀도. 두 엔진을 맞댈 때 **먼저 확인해야 하는 값**이다.
    dtype: str = "?"

    @abstractmethod
    def generate(self, system: str, prompt: str, *, log_samples: list[str] | None = None,
                 temp: float = 0.0, n: int = 1, max_tokens: int = 700) -> list[str]:
        """n개의 완성을 돌려준다. log_samples가 있으면 인용 제약을 건다."""


class MlxEngine(GenerationEngine):

    def __init__(self, model_path: str, adapter_path: str | None = None):
        from mlx_lm import load

        self.model, self.tok = load(model_path, adapter_path=adapter_path or None)
        # 두 엔진의 정밀도를 밖에서 맞대볼 수 있어야 한다. 안 보이면 또 어긋난다
        self.dtype = str(self.model.model.layers[0].self_attn.q_proj.weight.dtype)

    def generate(self, system, prompt, *, log_samples=None, temp=0.0, n=1, max_tokens=700):
        from mlx_lm import batch_generate, generate
        from mlx_lm.sample_utils import make_sampler

        text = self.tok.apply_chat_template(
            [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            tokenize=False, add_generation_prompt=True)
        sampler = make_sampler(temp=temp) if temp == 0.0 else make_sampler(temp=temp, top_p=0.95)
        procs = [CitationConstraint(self.tok, list(log_samples))] if log_samples else None
        if n == 1:
            return [generate(self.model, self.tok, text, max_tokens=max_tokens,
                             sampler=sampler, logits_processors=procs, verbose=False)]
        ids = [self.tok.encode(text)] * n
        return list(batch_generate(self.model, self.tok, ids, max_tokens=max_tokens,
                                   sampler=sampler, verbose=False).texts)


class TorchEngine(GenerationEngine):
    """HuggingFace transformers + peft. MPS를 쓴다.

    4bit는 이 경로에 없다. bitsandbytes에 MPS 지원이 없어서다. 그래서 MLX와 맞대려면
    **양쪽 다 fp16 비양자화**여야 한다(리포트 21번).
    """

    def __init__(self, model_path: str, adapter_path: str | None = None,
                 device: str = "mps", dtype: str = "auto"):
        """**정밀도를 하드코딩하지 않는다. 체크포인트에서 물려받는다.**

        처음에 float16으로 박아뒀다가 33종 중 23종이 MLX와 갈렸다. Qwen2.5의
        체크포인트는 bfloat16이고 MLX는 그것을 그대로 올리는데, torch만 float16으로
        내려서 지수부 범위가 달라졌다. 같은 가중치 같은 프롬프트 그리디인데 출력이
        딴판이 됐다.

        dtype="auto"면 transformers가 config의 dtype을 따르므로 MLX와 자동으로 맞는다.
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(model_path)
        resolved = dtype if dtype == "auto" else getattr(torch, dtype)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, dtype=resolved).to(device)
        if adapter_path:
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, adapter_path)
        self.model.eval()
        self.device = device
        self.dtype = str(next(self.model.parameters()).dtype)

    def generate(self, system, prompt, *, log_samples=None, temp=0.0, n=1, max_tokens=700):
        import torch
        from harness.constrained import TorchCitationProcessor

        text = self.tok.apply_chat_template(
            [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            tokenize=False, add_generation_prompt=True)
        enc = self.tok(text, return_tensors="pt").to(self.device)
        prompt_len = enc["input_ids"].shape[1]

        processors = None
        if log_samples:
            processors = [TorchCitationProcessor(
                CitationConstraint(self.tok, list(log_samples)), prompt_len)]

        # **생성 파라미터를 전부 명시한다. 물려받으면 안 된다.**
        # Qwen2.5의 generation_config.json에 repetition_penalty 1.1, top_k 20,
        # top_p 0.8이 들어 있고 HF는 이것을 조용히 적용한다. 반복 페널티는
        # do_sample=False인 그리디에서도 걸리므로, 명시하지 않으면 MLX의 그리디와
        # 다른 것을 재게 된다. 실제로 33종 중 23종이 갈렸다.
        # MLX의 make_sampler는 페널티 없음, top_k 비활성이 기본이라 거기에 맞춘다.
        kwargs = dict(max_new_tokens=max_tokens, num_return_sequences=n,
                      pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id,
                      repetition_penalty=1.0)
        if temp == 0.0:
            # 그리디에서는 top_k, top_p, temperature가 무효라 넘기면 경고만 난다
            kwargs.update(do_sample=False, temperature=None, top_p=None)
        else:
            kwargs.update(do_sample=True, temperature=temp, top_p=0.95, top_k=0)
        if processors:
            kwargs["logits_processor"] = processors

        with torch.no_grad():
            out = self.model.generate(**enc, **kwargs)
        # 프롬프트를 잘라내야 mlx의 generate와 같은 것을 돌려준다
        return [self.tok.decode(row[prompt_len:], skip_special_tokens=True) for row in out]


class LlamaCppEngine(GenerationEngine):
    """llama.cpp 서버를 같은 포트 뒤에 둔다. GGUF를 읽으므로 양자화 팔을 그대로 잰다.

    **어댑터를 얹는 개념이 없다.** GGUF는 병합된 가중치 하나이고, 팔의 값이 곧 모델 파일이다.

    **서버를 쓰는 이유가 둘이다.** 하나는 모델을 한 번만 올리는 것이고, 다른 하나는 이것이
    실제 배포에서 붙을 경로라는 것이다. 측정 경로와 배포 경로가 같아야 여기서 잰 값이
    그쪽에서도 성립한다.

    **채팅 템플릿을 서버가 적용한다(--jinja).** MLX와 torch는 tokenizer의 템플릿을 쓴다.
    출처가 같은 모델이라 같을 것으로 보지만 **같다고 가정하지 않는다.** 엔진 대조가
    확인하는 것이 정확히 그것이다.
    """

    #: gguf의 general.file_type. 실제로 올라간 가중치가 무엇인지 밖에서 보여야 한다
    _FILE_TYPES = {0: "F32", 1: "F16", 7: "Q8_0", 15: "Q4_K_M", 32: "BF16"}

    def __init__(self, model_path: str, adapter_path: str | None = None,
                 base_url: str | None = None, port: int = 18081, n_ctx: int = 4096,
                 timeout: float = 180.0):
        import atexit
        import subprocess
        import time
        import urllib.error
        import urllib.request

        if adapter_path:
            raise ValueError("llama.cpp 팔에는 어댑터를 얹지 않는다. 병합된 GGUF를 model_path로 준다")

        self.timeout = timeout
        self.dtype = self._read_file_type(model_path)
        self._proc = None

        if base_url:
            self.base_url = base_url.rstrip("/")
            return

        self.base_url = f"http://127.0.0.1:{port}"
        self._proc = subprocess.Popen(
            ["llama-server", "-m", model_path, "--port", str(port), "--jinja",
             "-c", str(n_ctx), "-ngl", "99", "--no-warmup"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        atexit.register(self.close)

        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"{self.base_url}/health", timeout=2) as res:
                    if res.status == 200:
                        return
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(0.5)
        self.close()
        raise RuntimeError(f"llama-server가 뜨지 않는다: {model_path}")

    def _read_file_type(self, model_path: str) -> str:
        try:
            from gguf import GGUFReader

            reader = GGUFReader(model_path)
            field = reader.fields["general.file_type"]
            value = int(field.parts[field.data[0]][0])
            return self._FILE_TYPES.get(value, f"file_type={value}")
        except Exception:
            return "?"

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except Exception:
                self._proc.kill()
        self._proc = None

    def generate(self, system, prompt, *, log_samples=None, temp=0.0, n=1, max_tokens=700):
        import json
        import urllib.request

        if log_samples:
            # 조용히 무시하면 제약 없는 값을 제약 있는 값으로 착각한다. GBNF 이식은 별건이다
            raise NotImplementedError("llama.cpp 인용 제약은 아직 없다. GBNF 이식이 선행되어야 한다")

        outs = []
        for i in range(n):
            # **샘플링 파라미터를 전부 명시한다.** HF가 generation_config의 반복 페널티를
            # 조용히 적용해 33종 중 23종이 갈린 적이 있다(리포트 22번). llama.cpp도 기본값이
            # 있으므로 같은 함정을 가정하고 전부 못박는다.
            payload = {
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": prompt}],
                "n_predict": max_tokens,
                "temperature": temp,
                "top_k": 0,
                "top_p": 1.0,
                "min_p": 0.0,
                "typical_p": 1.0,
                "repeat_penalty": 1.0,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0,
                "seed": 20260826 + i,
                "cache_prompt": False,
            }
            if temp > 0:
                payload["top_p"] = 0.95
            req = urllib.request.Request(
                f"{self.base_url}/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                body = json.loads(res.read().decode("utf-8"))
            outs.append(body["choices"][0]["message"]["content"])
        return outs


def make_engine(kind: str, model_path: str, adapter_path: str | None = None) -> GenerationEngine:
    if kind == "mlx":
        return MlxEngine(model_path, adapter_path)
    if kind == "torch":
        return TorchEngine(model_path, adapter_path)
    if kind == "llamacpp":
        return LlamaCppEngine(model_path, adapter_path)
    raise ValueError(f"모르는 엔진: {kind}")
