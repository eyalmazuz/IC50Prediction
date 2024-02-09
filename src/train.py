from src.model import IC50Bert
import torch
from typing import List, Dict, Tuple
from torch import nn
from torch import optim
from torch.utils.data import DataLoader
from tqdm import tqdm


class EarlyStopper:
    def __init__(self, patience: int = 1, min_delta: float = 0.0):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.min_validation_loss = float('inf')

    def early_stop(self, validation_loss: float):
        if validation_loss < self.min_validation_loss:
            self.min_validation_loss = validation_loss
            self.counter = 0
        elif validation_loss > (self.min_validation_loss + self.min_delta):
            self.counter += 1
            if self.counter >= self.patience:
                return True
        return False


class IC50BertTrainer:
    """
    Class used in the training of an IC50Bert model
    """

    def __init__(
        self,
        model: IC50Bert,
        train_dataloader: DataLoader,
        val_dataloader: DataLoader | None,
        num_epochs: int,
        criterion: nn.Module,
        optimizer: optim.Optimizer,
        device: torch.device = torch.device("cuda")
    ) -> None:
        self.model = model
        self.dataloader = train_dataloader
        self.val_dataloader = val_dataloader
        self.num_epochs = num_epochs
        self.criterion = criterion
        self.optimizer = optimizer
        self.device = device
        self.early_stopper = EarlyStopper(patience=10, min_delta=0.05)

    def train(self) -> Dict[str, List[float]]:
        """
        Train the specified model using the provided DataLoader, criterion and optimizer for number of epochs.
        :return: a Dict of average train and validation episode losses
        """
        self.model.to(self.device)
        self.criterion.to(self.device)
        avg_episode_losses = {"Train": [], "Validation": []}

        for epoch in range(self.num_epochs):
            self.model.train()
            total_loss = 0

            tqdm_dataloader = tqdm(
                self.dataloader, desc=f"Epoch {epoch+1}/{self.num_epochs}"
            )

            for batch in tqdm_dataloader:
                input_ids, token_type_ids, attention_mask, labels = self.get_from_batch(batch)

                self.optimizer.zero_grad()

                outputs = self.model(
                    ids=input_ids,
                    token_type_ids={"token_type_ids": token_type_ids},
                    mask=attention_mask,
                )

                loss = self.criterion(outputs, labels)
                loss.backward()
                self.optimizer.step()

                total_loss += loss.item()
                tqdm_dataloader.set_postfix(loss=loss.item())

            train_episode_loss = total_loss / len(self.dataloader)
            stop_loss = train_episode_loss
            avg_episode_losses["Train"].append(round(train_episode_loss, 4))
            results = f"Epoch {epoch + 1}/{self.num_epochs} | Loss: {train_episode_loss:.4f}"

            if self.val_dataloader:
                # Validation
                self.model.eval()  # Set the model to evaluation mode
                val_total_loss = 0

                with torch.no_grad():  # Disable gradient computation during validation
                    for val_batch in self.val_dataloader:
                        (
                            val_input_ids, val_token_type_ids, val_attention_mask, val_labels
                        ) = self.get_from_batch(val_batch)

                        val_outputs = self.model(
                            ids=val_input_ids,
                            token_type_ids={"token_type_ids": val_token_type_ids},
                            mask=val_attention_mask,
                        )

                        val_loss = self.criterion(val_outputs, val_labels)
                        val_total_loss += val_loss.item()

                val_episode_loss = val_total_loss / len(self.val_dataloader)
                stop_loss = val_episode_loss
                avg_episode_losses["Validation"].append(round(val_episode_loss, 4))
                results += f" | Val_Loss: {val_episode_loss:.4f}"

            # End of epoch
            print(results)
            if self.early_stopper.early_stop(stop_loss):
                print(f"\n--- Early stopping condition met! ---\n")
                break

        return avg_episode_losses

    def get_from_batch(self, batch) -> Tuple:
        input_ids = batch["input_ids"].to(self.device)
        token_type_ids = batch["token_type_ids"].to(self.device)
        attention_mask = batch["attention_mask"].type(torch.BoolTensor).to(self.device)
        labels = batch["labels"].to(self.device)
        return input_ids, token_type_ids, attention_mask, labels
