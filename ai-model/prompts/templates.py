DEFAULT_ERASE_PROMPT = "移除蒙版(图片二）区域中的内容，用周围背景自然填充"

ERASE_CONSTRAINT = "。保持画面其余部分不变，修复区域与周围环境自然融合，不要添加任何水印或文字(严厉静止添加水印)"


def build_erase_prompt(user_prompt: str) -> str:
    """将用户 prompt 包装为擦除场景指令，附加一致性约束"""
    user_prompt = (user_prompt or "").strip()
    if not user_prompt:
        user_prompt = DEFAULT_ERASE_PROMPT
    return f"{user_prompt}{ERASE_CONSTRAINT}"
