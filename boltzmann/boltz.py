import json
import logging
import os
import string
import subprocess
import yaml

logging.basicConfig(
    format  = '%(asctime)s %(levelname)-8s %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S.%f',
    level   = logging.INFO
)

from Bio.PDB import PDBParser, PDBIO, Select

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
    return os.path.join(models, '%s_model_%d.pdb' % (name, model_id))

# See the Boltz repository for details on these (and more) options:
# https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md#options
def run(folder, name, config, *,
    output_format     = 'pdb',
    recycling_steps   = None, #10,
    diffusion_samples = None, #25,
    use_msa_server    = False,
    override          = False,
    cache             = None
):
    inndir = os.path.join(folder, 'input')
    ootdir = os.path.join(folder, 'output')
    inyaml = os.path.join(inndir, name + '.yaml')

    os.makedirs(inndir, exist_ok=True)
    os.makedirs(ootdir, exist_ok=True)

    with open(inyaml, 'w') as file:
        yaml.dump(config, file)

    command = ['boltz', 'predict', inyaml, '--out_dir', ootdir]
    if output_format:
        command.append('--output_format')
        command.append(output_format)
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

    subprocess.run(command, stderr=subprocess.STDOUT, check=True)

def score_boltz(confidence_file):
    with open(confidence_file) as file:
        data = json.load(file)
    return {
        'boltz_confidence': data['confidence_score'],
        'boltz_ptm':        data['ptm'],
        'boltz_iptm':       data['iptm']
    }

def score_vina(pdb_file):
    base, ext = os.path.splitext(pdb_file)
    ligand    = base + '.lig'
    protein   = base + '.pro'

    # Use BioPython to separate proteins and ligands...
    split_model(pdb_file, protein + '.raw.pdb', chains='A')
    split_model(pdb_file, ligand  + '.raw.pdb', chains='B')

    # Use OpenBabel to add hydrogens and charges...
    # NOTE: Meeko seems to not expect hydrogens added to the protein, so we can just use the raw.
    # subprocess.run(['obabel', protein + '.raw.pdb', '-O', protein + '.pdb',  '-p', '7.4'], check=True)
    subprocess.run(['obabel', ligand  + '.raw.pdb', '-O', ligand  + '.mol2', '-p', '7.4'], check=True)

    # Use Meeko to convert to PDBQT files...
    subprocess.run(['/app/envs/meeko/bin/mk_prepare_receptor.py', '-i', protein + '.raw.pdb', '-o', protein, '--write_pdbqt'], check=True)
    subprocess.run(['/app/envs/meeko/bin/mk_prepare_ligand.py',   '-i', ligand  + '.mol2',    '-o', ligand + '.pdbqt'],        check=True)

    # Use AutoDock Vina to score in place...
    result = subprocess.run(['vina',
        '--receptor', protein + '.pdbqt',
        '--ligand',   ligand  + '.pdbqt',
        '--score_only',
        '--autobox'
    ], check=True)

    print(result.stdout)
    lines = result.stdout.splitlines()

    # Note: Using Andrew's line numbers:
    # 30) *Estimated Free Energy of Binding   : 0.000 (kcal/mol) [=(1)+(2)+(3)-(4)]\n
    # 31) *(1) Final Intermolecular Energy    : 0.000 (kcal/mol)\n
    # 32) *Ligand - Receptor                  : 0.000 (kcal/mol)\n
    # 33) *Ligand - Flex side chains          : 0.000 (kcal/mol)\n
    # 34) *(2) Final Total Internal Energy    : -0.019 (kcal/mol)\n
    # 35) *Ligand                             : -0.019 (kcal/mol)\n
    # 36) *Flex   - Receptor                  : 0.000 (kcal/mol)\n
    # 37) *Flex   - Flex side chains          : 0.000 (kcal/mol)\n
    # 38) *(3) Torsional Free Energy          : 0.000 (kcal/mol)\n
    # 39) *(4) Unbound System's Energy        : -0.019 (kcal/mol)\n"""

    return {
        'vina_score':                 float(lines[30].split(":")[-1].split()[0]),
        'vina_intermolecular_energy': float(lines[31].split(":")[-1].split()[0]),
        'vina_internal_energy':       float(lines[34].split(":")[-1].split()[0]),
        'vina_torsional_free_energy': float(lines[38].split(":")[-1].split()[0]),
        'vina_unbound_system_energy': float(lines[39].split(":")[-1].split()[0])
    }


def score_all(folder, name, diffusion_samples=1): #25):
    scores = [{'model_id': i} for i in range(diffusion_samples)]
    models = models_folder_for(folder, name)
    for i in range(diffusion_samples):
        conf_file = os.path.join(models, 'confidence_%s_model_%d.json' % (name, i))
        scores[i].update(score_boltz(conf_file))

        pdb_file = os.path.join(models, '%s_model_%d.pdb' % (name, i))
        scores[i].update(score_vina(pdb_file))

    return scores


class ChainSelector(Select):
    def __init__(self, chains, *args, **kwargs):
        self.chains = set(chains)

    def accept_chain(self, chain):
        return (chain.id in self.chains)

# Loosely based on https://stackoverflow.com/a/73196255
def split_model(input_pdb, output_pdb, chains):
    parser    = PDBParser(QUIET=True)
    structure = parser.get_structure('structure', input_pdb)

    io = PDBIO()
    io.set_structure(structure)
    io.save(output_pdb, ChainSelector(chains))
