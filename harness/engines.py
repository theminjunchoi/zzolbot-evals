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

    @abstractmethod
    def generate(self, system: str, prompt: str, *, log_samples: list[str] | None = None,
                 temp: float = 0.0, n: int = 1, max_tokens: int = 700) -> list[str]:
        """n개의 완성을 돌려준다. log_samples가 있으면 인용 제약을 건다."""


class MlxEngine(GenerationEngine):

    def __init__(self, model_path: str, adapter_path: str | None = None):
        from mlx_lm import load

        self.model, self.tok = load(model_path, adapter_path=adapter_path or None)

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
                 device: str = "mps", dtype: str = "float16"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, dtype=getattr(torch, dtype)).to(device)
        if adapter_path:
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, adapter_path)
        self.model.eval()
        self.device = device

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

        kwargs = dict(max_new_tokens=max_tokens, num_return_sequences=n,
                      pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id)
        if temp == 0.0:
            kwargs["do_sample"] = False       # 그리디. temperature는 넘기지 않는다
        else:
            kwargs.update(do_sample=True, temperature=temp, top_p=0.95)
        if processors:
            kwargs["logits_processor"] = processors

        with torch.no_grad():
            out = self.model.generate(**enc, **kwargs)
        # 프롬프트를 잘라내야 mlx의 generate와 같은 것을 돌려준다
        return [self.tok.decode(row[prompt_len:], skip_special_tokens=True) for row in out]


def make_engine(kind: str, model_path: str, adapter_path: str | None = None) -> GenerationEngine:
    if kind == "mlx":
        return MlxEngine(model_path, adapter_path)
    if kind == "torch":
        return TorchEngine(model_path, adapter_path)
    raise ValueError(f"모르는 엔진: {kind}")
