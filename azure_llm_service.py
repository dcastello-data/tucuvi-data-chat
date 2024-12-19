from openai import AzureOpenAI

class AzureLLMService:
    def __init__(
        self,
        azure_api_key: str,
        api_version: str,
        base_url: str,
        model: str,
        deployment_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 1
    ) -> None:
        self._openai = AzureOpenAI(
            api_key=azure_api_key,
            api_version=api_version,
            azure_endpoint=base_url,
            azure_deployment=deployment_id,
        )
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._top_p = top_p

    def execute(
        self,
        sys_prompt: str,
        usr_prompt: str = "",
        temperature: float | None = None,
        top_p: float | None = None
    ) -> tuple[str | None, int]:
        if temperature:
            self._temperature = temperature
        if top_p:
            self._top_p = top_p
        messages = [{"role": "system", "content": sys_prompt}]
        if usr_prompt:
            messages.append({"role": "user", "content": usr_prompt})
        completion = self._openai.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            top_p=self._top_p,
            messages=messages
        )
        choice = completion.choices[0]
        if choice.finish_reason != "stop":
            print(f"[Warning] Azure LLM could not get a valid response. Finish reason={choice.finish_reason}")
            return None, 500
        if choice.message.content is None:
            print(f"[Warning] Azure LLM invalid response (content=None)")
            return None, 500
        return choice.message.content, 200