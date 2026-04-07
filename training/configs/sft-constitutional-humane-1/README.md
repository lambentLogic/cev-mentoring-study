---
library_name: peft
model_name: sft-constitutional-humane-1
tags:
- base_model:adapter:./Qwen3.5-9B-Base-Humane-Interiority
- lora
- sft
- transformers
- trl
- unsloth
licence: license
pipeline_tag: text-generation
base_model: ./Qwen3.5-9B-Base-Humane-Interiority
---

# Model Card for sft-constitutional-humane-1

This model is a fine-tuned version of [None](https://huggingface.co/None).
It has been trained using [TRL](https://github.com/huggingface/trl).

## Quick start

```python
from transformers import pipeline

question = "If you had a time machine, but could only go to the past or the future once and never return, which would you choose and why?"
generator = pipeline("text-generation", model="None", device="cuda")
output = generator([{"role": "user", "content": question}], max_new_tokens=128, return_full_text=False)[0]
print(output["generated_text"])
```

## Training procedure

[<img src="https://raw.githubusercontent.com/wandb/assets/main/wandb-github-badge-28.svg" alt="Visualize in Weights & Biases" width="150" height="24"/>](https://wandb.ai/logical-luminosity/huggingface/runs/3cs1p069) 


This model was trained with SFT.

### Framework versions

- PEFT 0.18.0
- TRL: 0.24.0
- Transformers: 5.2.0
- Pytorch: 2.9.1
- Datasets: 4.3.0
- Tokenizers: 0.22.2

## Citations



Cite TRL as:
    
```bibtex
@misc{vonwerra2022trl,
	title        = {{TRL: Transformer Reinforcement Learning}},
	author       = {Leandro von Werra and Younes Belkada and Lewis Tunstall and Edward Beeching and Tristan Thrush and Nathan Lambert and Shengyi Huang and Kashif Rasul and Quentin Gallou{\'e}dec},
	year         = 2020,
	journal      = {GitHub repository},
	publisher    = {GitHub},
	howpublished = {\url{https://github.com/huggingface/trl}}
}
```