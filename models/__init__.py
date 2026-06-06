# -*- coding: utf-8 -*-
"""模型适配器工厂"""

from models.base_adapter import BaseModelAdapter
from config import MODELS, JUDGE_CONFIG


def create_adapter(model_id: str) -> BaseModelAdapter:
    """根据 model_id 创建对应的适配器实例"""
    if model_id not in MODELS:
        raise ValueError(f"未知模型: {model_id}，可选: {list(MODELS.keys())}")
    return BaseModelAdapter(model_id, MODELS[model_id])


def create_judge() -> BaseModelAdapter:
    """创建 Judge 模型适配器"""
    return BaseModelAdapter("judge", JUDGE_CONFIG)


def get_available_models() -> list[str]:
    """返回所有配置的模型ID列表"""
    return list(MODELS.keys())
