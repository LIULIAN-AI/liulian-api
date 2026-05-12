"""Model discovery endpoint.

Sprint Day 1 scope: list adapters registered on the liulian-python
research core. Real /predict + /predict-batch land on Day 2.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix='/models', tags=['models'])


class ModelCard(BaseModel):
    id: str
    name: str
    family: str
    capabilities: list[str]
    source: str  # 'liulian-core' | 'chronos' | 'gluonts' | 'tsl' | …
    parameters_M: float | None = None
    paper_url: str | None = None


# Day 1 catalog: hardcoded snapshot of liulian-python/liulian/models/torch/* + planned externals.
# Day 2: replace with a real registry that imports adapters and computes capabilities at runtime.
_CATALOG: list[ModelCard] = [
    # Classical
    ModelCard(id='lstm', name='LSTM', family='classical', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='transformer', name='Transformer', family='classical', capabilities=['deterministic'], source='liulian-core'),
    # Decomposition
    ModelCard(id='autoformer', name='Autoformer', family='decomposition', capabilities=['deterministic'], source='liulian-core', paper_url='https://arxiv.org/abs/2106.13008'),
    ModelCard(id='fedformer', name='FEDformer', family='decomposition', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='etsformer', name='ETSformer', family='decomposition', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='dlinear', name='DLinear', family='decomposition', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='lightts', name='LightTS', family='decomposition', capabilities=['deterministic'], source='liulian-core'),
    # Efficient attention
    ModelCard(id='informer', name='Informer', family='efficient', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='reformer', name='Reformer', family='efficient', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='ns_transformer', name='NonstationaryTransformer', family='efficient', capabilities=['deterministic'], source='liulian-core'),
    # Patch-based
    ModelCard(id='patchtst', name='PatchTST', family='patch', capabilities=['deterministic'], source='liulian-core', paper_url='https://arxiv.org/abs/2211.14730'),
    ModelCard(id='timexer', name='TimeXer', family='patch', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='timesnet', name='TimesNet', family='patch', capabilities=['deterministic'], source='liulian-core', paper_url='https://arxiv.org/abs/2210.02186'),
    # Mixture
    ModelCard(id='timemixer', name='TimeMixer', family='mixture', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='itransformer', name='iTransformer', family='mixture', capabilities=['deterministic'], source='liulian-core', paper_url='https://arxiv.org/abs/2310.06625'),
    # State-space
    ModelCard(id='mamba', name='Mamba', family='state-space', capabilities=['deterministic'], source='liulian-core', paper_url='https://arxiv.org/abs/2312.00752'),
    # LLM-grounded
    ModelCard(id='gpt4ts', name='GPT4TS', family='llm-grounded', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='timellm', name='TimeLLM', family='llm-grounded', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='timemoe', name='TimeMoE', family='llm-grounded', capabilities=['deterministic'], source='liulian-core'),
    # Domain custom
    ModelCard(id='swiss_lstm', name='Swiss-LSTM', family='domain', capabilities=['deterministic'], source='liulian-core'),
    ModelCard(id='swiss_transformer', name='Swiss-Transformer', family='domain', capabilities=['deterministic'], source='liulian-core'),
    # Planned externals (M2+)
    ModelCard(id='chronos-bolt', name='Chronos-Bolt', family='foundation', capabilities=['zero_shot', 'probabilistic', 'univariate', 'multivariate'], source='chronos', paper_url='https://arxiv.org/abs/2403.07815'),
    ModelCard(id='chronos-2', name='Chronos-2', family='foundation', capabilities=['zero_shot', 'probabilistic', 'univariate', 'multivariate', 'covariate'], source='chronos'),
]


@router.get('', response_model=list[ModelCard])
async def list_models(family: str | None = None, source: str | None = None) -> list[ModelCard]:
    """List registered models.

    Filters: `family` (classical / decomposition / efficient / patch /
    mixture / state-space / llm-grounded / domain / foundation),
    `source` (liulian-core / chronos / gluonts / tsl).
    """
    items = _CATALOG
    if family:
        items = [m for m in items if m.family == family]
    if source:
        items = [m for m in items if m.source == source]
    return items


@router.get('/{model_id}', response_model=ModelCard, responses={404: {'description': 'Not found'}})
async def get_model(model_id: str) -> ModelCard:
    from fastapi import HTTPException

    for m in _CATALOG:
        if m.id == model_id:
            return m
    raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': f'model {model_id!r} not registered'})
