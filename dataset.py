from typing import Dict, List, NamedTuple

import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer


class ProteinData(NamedTuple):
    ligand: str
    protein: str
    ic50: int


class ProteinSMILESDataset(Dataset):
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> ProteinData:
        row = self.df.iloc[idx]

        ligand = row["Ligand SMILES"]
        protein = row["BindingDB Target Chain Sequence"]
        target_ic50 = row["IC50 (nM)"]

        data = ProteinData(ligand, protein, target_ic50)

        return data


class TransformerCollate():
    def __init__(self, path: str) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(path)

    def __call__(self, batches: List[ProteinData]) -> Dict[str, torch.Tensor]:
        ligands = [item.ligand for item in batches]
        proteins = [item.protein for item in batches]
        target_ic50 = [item.ic50 for item in batches]

        encodings = self.tokenizer(
            ligands, proteins, padding=True, truncation=True, return_tensors="pt"
        )

        encodings["labels"] = torch.tensor(target_ic50)

        return encodings


def main() -> None:
    df = pd.read_csv("./BindingDB_EQ_IC50_Subset.tsv", sep="\t")

    dataset = ProteinSMILESDataset(df)

    collate_fn = TransformerCollate("Chem_Tokenizer_3")
    dataloader = DataLoader(dataset, batch_size=4, shuffle=True, collate_fn=collate_fn)

    print(dataset[0])

    batch = next(iter(dataloader))

    print(batch["input_ids"].shape)
    print(batch["token_type_ids"].tolist())


if __name__ == "__main__":
    main()
