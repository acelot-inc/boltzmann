import argparse
import sys

# Loosely based on https://stackoverflow.com/a/73196255
from Bio.PDB import PDBParser, PDBIO, Select


class ChainSelector(Select):
    def __init__(self, chains, *args, **kwargs):
        self.chains = set(chains)

    def accept_chain(self, chain):
        return (chain.id in self.chains)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name', default='structure')
    parser.add_argument('chains')
    parser.add_argument('pdb_file')
    args = parser.parse_args()

    parser    = PDBParser(QUIET=True)
    structure = parser.get_structure(args.name, args.pdb_file)

    io = PDBIO()
    io.set_structure(structure)
    io.save(sys.stdout, ChainSelector(args.chains))


if __name__ == '__main__':
    main()
