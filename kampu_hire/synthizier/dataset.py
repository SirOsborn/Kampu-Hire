import re
from typing import List, Tuple, Iterable, Union
import torch
from torch.utils.data import Dataset
import pandas as pd

NAME_LIST = [
    'Ahmed','Ling','Juan','Aisha','Sreyneang','Darika','Heng','Sreyneath',
    'John','Mary','David','Susan','James','Emily','Michael','Sarah', 'Alice',
    'Chen', 'Li', 'Nguyen', 'Patel', 'Kim', 'Lee', 'Wang', 'Zhang', 'Ali',
    'Fatima', 'Amina', 'Chloe', 'Zara', 'Liu', 'Mei', 'Xiu', 'Meredith', 'Uzi',
    'Zain', 'John', 'Brown', 'Smith', 'Doe', 'Emily', 'Davis', 'Olivia', 'Emma'
]


def anonymize_text(text: str) -> str:
    if not isinstance(text, str):
        return ''
    t = text
    t = re.sub(r'(?i)name\s*[:\-].*?(\n|$)', ' ', t)
    t = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', ' ', t)
    t = re.sub(r'\b\+?\d[\d\s().-]{6,}\b', ' ', t)
    t = re.sub(r'(?i)education\s*[:\-].*?(\n|$)', ' ', t)
    name_pattern = r'\b(' + '|'.join([re.escape(n) for n in NAME_LIST]) + r')\b'
    t = re.sub(name_pattern, ' name_token ', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


class ResumeDataset(Dataset):
    def __init__(
        self,
        csv_path: Union[str, Iterable[str]],
        vocab: dict[str,int] | None = None,
        max_vocab: int = 5000,
        skill_keywords: List[str] | None = None,
        underserved_keywords: List[str] | None = None,
        skill_boost: float = 1.0,
        underserved_boost: float = 1.0,
    ):
        # load 1 or many CSVs
        if isinstance(csv_path, str):
            dfs = [pd.read_csv(csv_path)]
        else:
            dfs = [pd.read_csv(p) for p in csv_path]
        df = pd.concat(dfs, ignore_index=True).dropna(subset=['Category','Resume'])
        self.labels, self.texts = df['Category'].tolist(), df['Resume'].tolist()
        # keyword sets (lowercase)
        self.skill_set = set([s.lower() for s in (skill_keywords or [])])
        self.underserved_set = set([s.lower() for s in (underserved_keywords or [])])
        self.skill_boost = float(skill_boost)
        self.underserved_boost = float(underserved_boost)
        # Build vocab if not provided (simple token counts)
        if vocab is None:
            from collections import Counter
            counts = Counter()
            for t in self.texts:
                toks = re.findall(r'\b\w+\b', anonymize_text(t).lower())
                counts.update(toks)
            most = counts.most_common(max_vocab)
            self.vocab = {w:i for i,(w,_) in enumerate(most)}
        else:
            self.vocab = vocab
        self.label_to_idx = {c:i for i,c in enumerate(sorted(set(self.labels)))}
        self.idx_to_label = {i:c for c,i in self.label_to_idx.items()}

    def __len__(self):
        return len(self.texts)

    def vectorize(self, text: str) -> torch.Tensor:
        toks = re.findall(r'\b\w+\b', anonymize_text(text).lower())
        x = torch.zeros(len(self.vocab), dtype=torch.float32)
        for tok in toks:
            if tok in self.vocab:
                weight = 1.0
                if tok in self.skill_set:
                    weight *= self.skill_boost
                if tok in self.underserved_set:
                    weight *= self.underserved_boost
                x[self.vocab[tok]] += weight
        return x

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        x = self.vectorize(self.texts[idx])
        y = self.label_to_idx[self.labels[idx]]
        return x, y
