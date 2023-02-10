""" Push Models to Modelhub"""
import os
import argparse
import logging
import shutil
from distutils.dir_util import copy_tree
from os.path import join as pj
from huggingface_hub import create_repo

import transformers
from lmqg.lmqg_cl.readme_template import get_readme

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')


def main():
    parser = argparse.ArgumentParser(description='Push to Model hub')
    parser.add_argument('-m', '--model-checkpoint', required=True, type=str)
    parser.add_argument('-a', '--model-alias', required=True, type=str)
    parser.add_argument('-o', '--organization', required=True, type=str)
    parser.add_argument('--use-auth-token', help='Huggingface transformers argument of `use_auth_token`',
                        action='store_true')
    parser.add_argument('--skip-model-upload', help='', action='store_true')
    parser.add_argument('--access-token', default=None, type=str)
    opt = parser.parse_args()

    assert os.path.exists(pj(opt.model_checkpoint, "pytorch_model.bin")), pj(opt.model_checkpoint, "pytorch_model.bin")
    logging.info(f"Upload {opt.model_checkpoint} to {opt.organization}/{opt.model_alias}")

    # url = create_repo(opt.model_alias, organization=opt.organization, exist_ok=True)
    url = create_repo(repo_id=f"{opt.organization}/{opt.model_alias}", exist_ok=True, repo_type="model")

    if not opt.skip_model_upload:
        tokenizer = transformers.AutoTokenizer.from_pretrained(opt.model_checkpoint, local_files_only=True)
        config = transformers.AutoConfig.from_pretrained(opt.model_checkpoint, local_files_only=True)
        if config.model_type == 't5':  # T5 model requires T5ForConditionalGeneration class
            model_class = transformers.T5ForConditionalGeneration.from_pretrained
        elif config.model_type == 'mt5':
            model_class = transformers.MT5ForConditionalGeneration.from_pretrained
        elif config.model_type == 'bart':
            model_class = transformers.BartForConditionalGeneration.from_pretrained
        elif config.model_type == 'mbart':
            model_class = transformers.MBartForConditionalGeneration.from_pretrained
        else:
            raise ValueError(f'unsupported model type: {config.model_type}')

        if opt.access_token is not None:
            model = model_class(opt.model_checkpoint, config=config, local_files_only=True, hub_token=opt.access_token)
        else:
            model = model_class(opt.model_checkpoint, config=config, local_files_only=True)
        args = {"repo_id": f"{opt.organization}/{opt.model_alias}", "use_auth_token": opt.use_auth_token}
        model.push_to_hub(**args)
        tokenizer.push_to_hub(**args)
        config.push_to_hub(**args)


    # upload remaining files
    copy_tree(f"{opt.model_checkpoint}", f"{opt.model_alias}")

    # config
    readme = get_readme(
        model_name=f"{opt.organization}/{opt.model_alias}",
        model_checkpoint=opt.model_checkpoint
    )
    with open(pj(opt.model_checkpoint, "README.md"), 'w') as f:
        f.write(readme)

    # upload remaining files
    copy_tree(f"{opt.model_checkpoint}", f"{opt.model_alias}")
    os.system(
        f"cd {opt.model_alias} && git lfs install && git add . && git commit -m 'model update' && git push && cd ../")
    shutil.rmtree(f"{opt.model_alias}")  # clean up the cloned repo
