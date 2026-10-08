"""AI 解读客户端：仅在用户主动点击并已配置接口时，才向外部发起请求。

兼容 OpenAI Chat Completions 协议（/v1/chat/completions 风格）。
"""
import json
import urllib.request
import urllib.error


class AIError(Exception):
    pass


SYSTEM_PROMPT = (
    "你是一位精通中国传统八字命理的分析师。用户会提供一份由程序精确排出的八字命盘"
    "以及规则引擎的初步结论。请基于提供的盘面数据进行分析，要求：\n"
    "1. 先复述确认关键盘面信息（四柱、日主、月令、旺衰），确保理解无误；\n"
    "2. 从五行喜忌、十神格局、性格倾向、事业财运、感情人际、健康提示等角度分点论述；\n"
    "3. 结合当前大运与流年给出趋势性建议；\n"
    "4. 语言客观平实，条理清晰，使用中文与 Markdown；\n"
    "5. 明确指出这是传统文化视角的参考，不构成医疗、投资、婚姻等重大决策依据；\n"
    "6. 若盘面信息不足或存在歧义（如出生时间接近节气交界），请主动指出不确定性。"
)


def chat(cfg, user_content, timeout=90):
    base = (cfg.get("base_url") or "").strip().rstrip("/")
    key = (cfg.get("api_key") or "").strip()
    model = (cfg.get("model") or "").strip()

    if not base:
        raise AIError("尚未配置 AI 接口地址（base_url）。")
    if not model:
        raise AIError("尚未配置模型名称（model）。")

    url = base + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": cfg.get("temperature", 0.7),
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("Authorization", "Bearer " + key)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        raise AIError(f"接口返回错误 HTTP {e.code}：{detail}")
    except urllib.error.URLError as e:
        raise AIError(f"无法连接到接口：{e.reason}")
    except Exception as e:
        raise AIError(f"请求失败：{e}")

    try:
        obj = json.loads(body)
        return obj["choices"][0]["message"]["content"]
    except Exception:
        raise AIError("接口返回格式无法解析：" + body[:300])