from typing import Type, List

from jinja2 import TemplateSyntaxError, Environment, DebugUndefined

from sqlalchemy.orm import joinedload
from ..models.all import PromptVersion
from ..models.enums.all import MessageRoles
from ..models.pd.predict import PromptVersionPredictModel, PromptVersionPredictStreamModel, PromptMessagePredictModel
from tools import db
from pylon.core.tools import log


def _resolve_variables(text, vars) -> str:
    environment = Environment(undefined=DebugUndefined)
    ast = environment.parse(text)
    template = environment.from_string(text)
    return template.render(vars)


def prepare_payload(
        data: dict,
        pd_model: Type[PromptVersionPredictModel] | Type[PromptVersionPredictStreamModel]
) -> PromptVersionPredictModel | PromptVersionPredictStreamModel:
    payload = pd_model.parse_obj(data)
    if payload.prompt_version_id:
        with db.with_project_schema_session(payload.project_id) as session:
            query_options = []
            if not payload.variables:
                query_options.append(joinedload(PromptVersion.variables))
            if not payload.messages:
                query_options.append(joinedload(PromptVersion.messages))

            prompt_version = session.query(PromptVersion).options(*query_options).get(payload.prompt_version_id)
            prompt_version.project_id = payload.project_id
            prompt_version_pd = pd_model.from_orm(prompt_version)
            payload = prompt_version_pd.merge_update(payload)
    log.info(f'{payload=}')
    return payload


class CustomTemplateError(Exception):
    def __init__(self, msg: str, loc: list):
        self.msg = msg
        self.type = 'CustomTemplateError'
        self.loc = loc
        super().__init__(self.msg)

    def errors(self) -> List[dict]:
        return [{'ok': False, 'msg': self.msg, 'type': self.type, 'loc': self.loc}]


def prepare_conversation(payload: PromptVersionPredictStreamModel) -> List[dict]:
    variables = {v.name: v.value for v in payload.variables}
    messages = []

    if payload.context:
        try:
            messages.append(
                PromptMessagePredictModel(
                    role=MessageRoles.system,
                    content=_resolve_variables(
                        payload.context,
                        variables
                    )
                ).dict(exclude_unset=True)
            )
        except TemplateSyntaxError:
            raise CustomTemplateError(msg='Context template error', loc=['context'])

    for idx, i in enumerate(payload.messages):
        message = i.dict(exclude={'content'}, exclude_none=True, exclude_unset=True)
        try:
            message['content'] = _resolve_variables(i.content, variables)
        except TemplateSyntaxError:
            raise CustomTemplateError(msg='Message template error', loc=['messages', idx])
        messages.append(message)

    if payload.chat_history:
        for i in payload.chat_history:
            messages.append(i.dict(exclude_unset=True))

    if payload.user_input:
        messages.append(
            PromptMessagePredictModel(
                role=MessageRoles.user,
                content=payload.user_input,
                name=payload.user_name
            ).dict(exclude_unset=True, exclude_none=True)
        )
    return messages
