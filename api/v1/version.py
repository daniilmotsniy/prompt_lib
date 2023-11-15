import json
from itertools import chain
from flask import request

from pylon.core.tools import log
from tools import api_tools, auth, config as c, db

from ...models.all import PromptVersion
from ...models.pd.detail import PromptVersionDetailModel
from ...utils.constants import PROMPT_LIB_MODE


class PromptLibAPI(api_tools.APIModeHandler):
    def get(self, project_id: int, prompt_id: int, version_id: int, **kwargs):
        with db.with_project_schema_session(project_id) as session:
            prompt_version = session.query(PromptVersion).filter(
                PromptVersion.id == version_id,
                PromptVersion.prompt_id == prompt_id
            ).first()
            if not prompt_version:
                return {'error': f'Prompt[{prompt_id}] version[{version_id}] not found'}, 400
            version_details = PromptVersionDetailModel.from_orm(prompt_version)
            version_details.author = auth.get_user(user_id=prompt_version.author_id)
            return json.loads(version_details.json()), 200

    def post(self, project_id: int, prompt_id: int, **kwargs):
        # prompt_data = self.module.get_by_id(project_id, request.json['prompt_id'])
        # prompt_data.pop('test_input')
        # prompt_data.update({'version': request.json['version']})
        # prompt = self.module.create(project_id, prompt_data)
        # for i in chain(prompt_data['variables'], prompt_data['examples']):
        #     i['prompt_id'] = prompt['id']
        # self.module.create_variables_bulk(project_id, prompt_data['variables'])
        # self.module.create_examples_bulk(project_id, prompt_data['examples'])
        # self.module.update_tags(project_id, prompt['id'], prompt_data['tags'])
        # return prompt, 201
        return None, 400


class API(api_tools.APIBase):
    url_params = api_tools.with_modes([
        '<int:project_id>/<int:prompt_id>/<int:version_id>',
    ])

    mode_handlers = {
        PROMPT_LIB_MODE: PromptLibAPI,
    }