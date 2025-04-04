import os
import string
import subprocess
import yaml

class Sequence:
    def __init__(self, type, info):
        self.type = type
        self.info = info

    def config(self, chain_id):
        return {self.type: {**self.info, 'id': chain_id}}

class ProteinSequence(Sequence):
    def __init__(self, sequence, msa_file=None):
        super(ProteinSequence, self).__init__('protein', {'sequence': sequence})
        if msa_file is not None:
            self.info['msa'] = msa_file

class SmilesSequence(Sequence):
    def __init__(self, smiles):
        super(SmilesSequence, self).__init__('ligand', {'smiles': smiles})


def config_for(sequences, chain_ids=string.ascii_uppercase):
    return {
        'version':   1,
        'sequences': [seq.config(cid) for seq, cid in zip(sequences, chain_ids)]
    }

def models_folder_for(folder, name):
    return os.path.join(folder, 'output', 'boltz_results_' + name, 'predictions', name)

def model_path(folder, name, model_id):
    models = models_folder_for(folder, name)
    return os.path.join(models, '%s_model_%d.cif' % (name, model_id))

# See the Boltz repository for details on these (and more) options:
# https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md#options
def run(folder, name, config, *,
    recycling_steps   = 10,
    diffusion_samples = 25,
    use_msa_server    = False,
    override          = False,
    cache             = None
):
    inndir = os.path.join(folder, 'input')
    ootdir = os.path.join(folder, 'output')
    config = os.path.join(inndir, name + '.yaml')

    os.makedirs(inndir, exist_ok=True)
    os.makedirs(ootdir, exist_ok=True)

    with open(config, 'w') as file:
        yaml.dump(config, file)

    command = ['boltz', 'run', config]
    if override:
        command.append('--override')
    if use_msa_server:
        command.append('--use_msa_server')
    if recycling_steps is not None:
        command.append('--recycling_steps')
        command.append(str(recycling_steps))
    if diffusion_samples is not None:
        command.append('--diffusion_samples')
        command.append(str(diffusion_samples))
    if cache:
        command.append('--cache')
        command.append(str(cache))

    subprocess.run(command)

def score_boltz(confidence_file):
    with open(confidence_file) as file:
        data = json.load(file)
    return {
        'boltz_confidence': data['confidence_score'],
        'boltz_ptm':        data['ptm'],
        'boltz_iptm':       data['iptm']
    }

def score_vina(cif_file):
    pass

def score_all(folder, name, diffusion_samples=25):
    scores = [{'model_id': i} for i in range(diffusion_samples)]
    models = models_folder_for(folder, name)
    for i in range(diffusion_samples):
        conf_file = os.path.join(models, 'confidence_%s_model_%d.json' % (name, i))
        scores[i].update(score_boltz(conf_file))

        # cif_file = os.path.join(model_folder, '%s_model_%d.cif' % (name, i))
        # scores[i].update(score_vina(conf_file))

    return scores
