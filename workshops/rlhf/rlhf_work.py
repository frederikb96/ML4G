#!/usr/bin/env python
# coding: utf-8

# <a href="https://colab.research.google.com/github/EffiSciencesResearch/ML4G/blob/main/workshops/rlhf/rlhf.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>
# 
# 
# This workshop was made by Callum McDougal for ARENA, and serves two purposes:
# - Play around RLHF
# - Familiarize with new libraries that might be useful for some of your future projects (HuggingFace, Weights&Biases, TRLX)

# # Reinforcement Learning from Human Feedback
# 
# 
# ## Introduction
# 
# 
# ### Context - Pretraining is not enough
# 
# You've seen earlier in the course that we can train very large and performant models like GPT2 using next-token prediction. Such models, prior to any fine-tuning, must be steered carefully with prompts in order to generate useful output. Most language models used in services of any kind today are not only pre-trained models. Rather, we use many training techniques to make them more useful.
# 
# RLHF is one of many techniques which can convert a pre-trained model, into a more useful model for practical application.
# 
# ### Context - RLHF as a naive alignment strategy
# 
# The field AI alignment is concerned with aligning AI systems with our desired outcomes. There are many reasons to think that intelligent systems do not, by default, share human values or that whilst training against any objective will lead to reliable, expected outcomes being produced by AI systems. Nevertheless, training AI systems to produce outcomes that humans prefer over outcomes which they don't seems to be a concrete step towards AI alignment, which we can build on later.
# 
# Thus we get the core idea of RLHF as an alignment strategy. We care about outcomes, so we provide the AI feedback based on what we think likely outcomes of it's actions are and update it to produce good outcomes according to our preferences.
# 
# For more detail on RLHF, see Paul Christiano's blog post [here](https://www.alignmentforum.org/posts/vwu4kegAEZTBtpT6p/thoughts-on-the-impact-of-rlhf-research#The_case_for_a_positive_impact).
# 
# 
# ### What is RLHF?
# 
# Reinforcement Learning with Human Feedback (RLHF) is a RL technique where the rewards issued by a reward model, which is itself trained from labelled data from a human operator. Often, it can be hard to specify the reward function $R : S \times A \to \mathbb{R}$ that the environment uses to issue reward to the agent, so we ask a human instead to reward/punish the agent based on the action it took. [OpenAI](https://openai.com/research/learning-from-human-preferences) uses RLHF to adjust the behaviour of models to desirable behaviour, but this can also incentivise the agent to hack the reward signal (by taking actions that look good to the human, or influencing the human to always give good rewards.)
# 
# One should note that in the framework of RLHF, the environment only has one state, and the model that we are trying to fine-tune with RLHF no longer needs to "plan ahead", so in this sense it is closer to a bandit problem than the MDPs we saw in previous days.
# 
# ### Why does it matter?
# 
# RLHF (at the moment) is a successful method of nudging large language models towards desired behaviour when that behaviour is difficult to write as an algorithm.
# 
# For chess, it's easy to evaluate whether an agent won/lost the game, so we can reward that directly. For text generation, it can be hard to formally specify
# what we mean by harmful or abusive text. One could have simple proxies like a filter to encourage/discourge use of particular words, and use that
# to train against, but it's very easy to construct harmful text such that no particular word in the sentence would be classed as offensive:
# "I would love to eat your pet puppy" contains no offensive words, even though the semantic meaning of the entire sentence is quite offensive.
# A simple proxy for offensiveness might even rate this as a positive statement, as it contains "nice" words like *love* and *puppy*.
# 
# However, samples from humans are expensive and slow. Even running a single batch of examples through the model could take a long time
# if we need a human to give a scalar reward for each action chosen by the model. So, the solution is to collect a lot of data from a human
# (a set of (observation, action, reward) tuples), train a reward model on this data, and then use the reward model as the reward function.
# 
# 
# ### How does RLHF work in practice?
# 
# RLHF involves 3 stages:
# 
# 1. We pretrain a language model (LM) using existing supervised learning techniques.
# 2. We gather labelled data from humans, and train a reward model that will act as a proxy for the human's rewards.
# 3. We fine-tuning the LM with reinforcement learning.
# 
# #### 1. Pretraining
# 
# Since reinforcement learning is very sample inefficient, it is unreasonable to expect to be able to train a language model from scratch using online learning. Rather, we must start with an existing pre-trained model and then fine-tune it.
# 
# We will be using GPT-2-small as our base model to finetune.
# 
# <img src="https://raw.githubusercontent.com/jbloomAus/ARENA_2.0-RLHF/main/media/pretraining.png" width="500">
# 
# #### 2. The Reward Model
# 
# The reward model is used to assign a reward to any given output of the model during training.
# Rather than have reward be a simple function of the state of the world (as for RL environments like CartPole),
# the reward model assigns a reward to a given piece of text.
# The reward model acts like a text classifier, rewarding "good" pieces of text, and punishing "bad" text.
# 
# The reward model is trained on a set of prompts, hand labelled by humans into "good" and "bad".
# This is then used to train the reward model, to act as a stand-in for the human during the fine-tuning stage.
# 
# The model acts as a mapping between arbitrary text and human preferences.
# 
# <img src="https://raw.githubusercontent.com/jbloomAus/ARENA_2.0-RLHF/main/media/reward-model.png" width="700">
# 
# #### 3. Fine-Tuning with Reinforcement Learning
# 
# Finally, given some reward model and some pre-trained model, we can use an algorithm such as PPO to reward the model for producing prompt completions when the reward model predicts the completion to be preferable.
# 
# In the standard RL framework, the agent recieves a reward on every timestep during interaction.
# Here, the "observation" that the agent receives is a textual prompt, and the "action" the agent takes is the choice of words
# to complete the prompt. The reward model then assigns a reward based on the prompt together with the completion from the agent,
# which is then used to compute the loss, and update the weights of the model.
# 
# <img src="https://raw.githubusercontent.com/jbloomAus/ARENA_2.0-RLHF/main/media/rlhf.png" width="800">
# 
# ### How does RLHF differ from PPO?
# 
# - No "environment". RLHF operates on text completions made by the pre-trained generative model.
# - Reward Model. Reward itself is generated by the reward model which itself must be trained.
# - Adding a Value Head. We add a value head to the policy/LM architecture so that we have both an actor and a critic for PPO.
# - KL Divergence penalty. The KL divergence term penalizes the RL policy from moving substantially away from the initial pretrained model with each training batch, to ensure we maintain coherent outputs, and the fine-tuned model avoids generating text that overfits to what the reward model is looking for.
# 
# #### Aside - value heads
# 
# The "actor" in our PPO setup is the GPT model. We get the "critic" by adding a **value head** to the GPT architecture - i.e. you stick a classifier to GPT2 and train that as our value function.
# 
# For an example, see the source code for AutoModelForCausalLMWithValueHead in the [TRLX github](https://github.com/CarperAI/trlx/blob/main/trlx/models/modeling_ppo.py). This gives us an autoregressive transformer which has 2 outputs: one corresponding to the standard next token prediction objective, and one which sticks a classifier on the end to get a value function. It does this by adding `self.v_head`, a function which reads from the final value of the residual stream in GPT (which stores some compressed embedding of the prompt), and extracts a value function from this representation. You can think of this as a kind of feature extraction, analogous to the feature extraction that we implemented with our ResNet models in the first week.
# 
# The TRLX library we'll be working with today handles all of this under the hood. However, you should definitely have a poke around this library to get a feel for how it works.
# 
# #### Aside - KL divergence term
# 
# **Note** - the KL div penalty is not the same as the version of PPO which uses a KL div penalty term in the surrogate objective function. The first one is a feature of the RLHF setup; it makes sure we don't get too far from the original model (i.e. it's static throughout training, used to constrain how much we change from the original model by the end). The second one is a feature of PPO setup; it makes sure we don't make huge updates from where we were before the last training step (i.e. it's a moving target, used to constrain how much we change each step).
# 
# The KL div term we use in RL heavily penalises our new model when it outputs something which **would have low probability in the original model.** This is related to the reason RLHF'ed models are sometimes described as ["lobotomized"](https://twitter.com/repligate/status/1640488734192726018) - they converge to a subset of the kinds of outputs that our original model might have had, meaning they lose some of the variance and creativity of the original model.
# 
# ## Optionnal readings for RLHF
# 
# * [Fine-Tuning Language Models from Human Preferences](https://arxiv.org/abs/1909.08593) (paper)
# * [Learning to summarize from human feedback](https://arxiv.org/abs/2009.01325) (paper)
# * [AI safety via debate](https://openai.com/research/debate) (OpenAI blog post)
# * [Thoughts on the impact of RLHF research](https://www.alignmentforum.org/posts/vwu4kegAEZTBtpT6p/thoughts-on-the-impact-of-rlhf-research), by Paul Christiano
# 
# ## Content & Learning Objectives
# 
# 
# #### 1️⃣ Prompt Dataset & Reward Model
# 
# In the first section, we'll get set up with the prompt dataset and reward model we'll be using for the rest of the exercises.
# 
# > ##### Learning objectives
# >
# > * Learn about the BERT transformer model and how it can be used for sentiment analysis
# > * Load datasets from Huggingface and break them up into prompts
# > * Generate text from Huggingface models
# > * Output positive sentiments from models in vanilla PyTorch and Huggingface pipelines
# 
# #### 2️⃣ Using RLHF for Finetuning
# 
# In the second section, we'll finetune a model pre-trained on the IMDB dataset using RLHF to generate positive reviews.
# 
# > ##### Learning objectives
# >
# > - Learn about TRLX and how it can be used
# > - Using RLHF to improve sentiment of GPT2 produced Movie Reviews
# 
# ## Setup

# In[1]:


#get_ipython().system('pip install datasets transformers
# git+https://github.com/CarperAI/trlx.git')


# In[2]:


import os

import json
import sys
import math
import gc
from pathlib import Path
import torch
from datasets import load_dataset
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
)
from transformers.models.bert.modeling_bert import BertForMaskedLM
import logging
from typing import cast, Any, List, Optional, Union, Tuple

from trlx import train
from trlx.data.default_configs import (
    TRLConfig,
    TrainConfig,
    OptimizerConfig,
    SchedulerConfig,
    TokenizerConfig,
    ModelConfig,
)
from trlx.models.modeling_ppo import PPOConfig


# # 1️⃣ Prompt Dataset & Reward Model
# 
# 
# > ##### Learning objectives
# >
# > * Learn about the BERT transformer model and how it can be used for sentiment analysis
# > * Load datasets from Huggingface and break them up into prompts
# > * Generate text from Huggingface models
# > * Output positive sentiments from models in vanilla PyTorch and Huggingface pipelines
# 
# ## Background - BERT
# 
# In the transformers chapter, we only worked with autoregressive transformers like GPT2. Here, we'll work with BERT, a well-known **bidirectional transformer**.
# 
# BERT predates GPT2 slightly (it was released in 2018, one year after the seminal "Attention is all you need" paper). It was the next in a proud tradition of naming transformers after muppets (no, [that's](https://arxiv.org/pdf/1910.13034.pdf) [not](https://arxiv.org/pdf/1904.09223.pdf) [a](https://arxiv.org/pdf/1905.12616.pdf) [joke](https://arxiv.org/pdf/1906.01604.pdf)). It has bidirectional attention, meaning we don't apply masking to the attention patterns - information can flow backwards and forwards in the model. BERT is usually used for classification tasks, such as sentiment analysis.
# 
# ### How is BERT trained?
# 
# The architecture is similar to GPT, although the "core BERT" model doesn't have an unembedding (i.e. the output has shape `(batch, seq_len, d_model)`).
# 
# BERT is trained on two kinds of tasks: **next sentence prediction** (NSP) and **masked language modelling** (MLM).
# 
# * In MLM, we take a sequence and replace some of its tokens with a special `[MASK]` token, then train the model to predict the original token.
# * In NSP, we take two sentences, and train the model to predict whether the second sentence follows the first (we do this by adding a small classifier at the end of BERT, which just reads from the final value of the residual stream at the zeroth sequence position, which is a special classification token `[CLS]`).
# 
# Importantly, **both of these two tasks require the model to learn some kind of compressed representation of the input sequence** in its residual stream.
# 
# ### How do we turn BERT into a classifier?
# 
# We usually stick a classification head onto the end of the "core BERT architecture" at the `[CLS]` token, then take the pretrained model and fine-tune it on a classification task. If pretraining has been successful, the model will have learned some kind of compressed representation of the input sequence in its residual stream, and the classifier will be doing something like feature extraction.
# 
# In the RLHF exercises you'll be taking advantage of BERT's ability to be used as a classifier, but for now we'll have a look at how BERT does at masked language modelling.
# 
# ### Exercise - load BERT, and play around with it
# 
# ```c
# Difficulty: 🟠⚪⚪⚪⚪
# Importance: 🟠🟠🟠⚪⚪
# 
# You should spend up to 10-15 minutes on this exercise.
# ```
# 
# We're going to use a HuggingFace tokenizer for now to encode text into a sequence of tokens that our model can use. The tokenizer has to match the model - our model was trained with the `bert-base-cased` tokenizer which is case-sensitive. If you tried to use the `bert-base-uncased` tokenizer which is case-insensitive, it wouldn't work at all.
# 
# Check out `tokenizer.vocab` to get an idea of what sorts of strings are assigned to tokens. In WordPiece, tokens represent a whole word unless they start with `##`, which denotes this token is part of a word.
# 
# You can also check out `tokenizer.special_tokens_map`. The strings here are mapped to tokens which have special meanings - for example `tokenizer.mask_token`, which is the literal string '[MASK]', is converted to `tokenizer.mask_token_id`, equal to 103.
# 
# **Play around with this model**, until you get a sense of how it works. What kind of interesting completions can you find? Can BERT solve the IOI task? Can it do basic arithmetic?
# 

# In[3]:


bert = BertForMaskedLM.from_pretrained("bert-base-cased")
bert_tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")


# In[9]:


def predict(model: BertForMaskedLM, tokenizer: AutoTokenizer, text: str, k=15) -> List[List[str]]:
    """
    Return a list of k strings for each [MASK] in the input.
    """

    # Make sure we're in eval mode
    model.eval()

    # Tokenizer returns a bunch of special BERT-specific things, we just want input ids
    input_ids = tokenizer(text, return_tensors="pt")["input_ids"]

    # Get top predictions at all the places we masked
    out = model(input_ids).logits
    preds = out[input_ids == tokenizer.mask_token_id]
    tops = preds.topk(k, dim=-1).indices

    return [[tokenizer.decode(t) for t in mask] for mask in tops]


your_text = "The Answer to the question of [MASK] is 42."
predictions = predict(bert, bert_tokenizer, your_text, k=1)
print("Model predicted: \n", "\n".join(map(str, predictions)))


# ## IMDB dataset
# 
# 
# First, load in the IMDB user reviews dataset. Documentation about the IMDB dataset can be found here: https://huggingface.co/datasets/imdb. We want to use both the train and test splits to collect prompts.

# In[10]:


imdb = load_dataset("imdb", split="train+test")


# ### Exercise - Figure out the positive-negative review split in the dataset
# 
# ```c
# Difficulty: 🟠⚪⚪⚪⚪
# Importance: 🟠🟠⚪⚪⚪
# 
# You should spend up to 5 minutes on this exercise.
# ```
# 
# The positive-negative review split will tell us the distribution of sentiments our model will output out of the box. Write a function to print out the number of samples for each label.
# 
# You should review the [documentation page](https://huggingface.co/datasets/imdb) to know more what the dataset looks like.
# 
# <details>
# <summary><b>Hint</b> (click to expand)</summary>
# - You can access specific columns of the dataset using the `dataset['column_name']` syntax.
# - You can use the `.count(value)` method on a column to count the number of occurences of a value in that column.
# </details>

# In[17]:


def label_split(dataset) -> Tuple[int, int]:
    return dataset['label'].count(1), dataset['label'].count(0)

nb_positive, nb_negative = label_split(imdb)

print(f"Number of positive reviews: {nb_positive}")
print(f"Number of negative reviews: {nb_negative}")


# <details>
# <summary>Solution</summary>
# 
# 
# ```python
# def label_split(dataset) -> Tuple[int, int]:
#     positive_samples = dataset['label'].count(1)
#     negative_samples = dataset['label'].count(0)
# 
#     return postive_samples, negative_samples
# ```
# </details>
# 
# 
# ### Exercise - Create a set of prompts
# 
# ```c
# Difficulty: 🟠🟠⚪⚪⚪
# Importance: 🟠🟠🟠⚪⚪
# 
# You should spend up to ~10 minutes on this exercise.
# ```
# 
# A prompt to the model can look like "Today was not fun ", "In the event of " or "Mary gave John a ". These prompts will serve as the starting point for model generations during the RLHF process.
# 
# In the context of the exercise to push GPT2 towards outputting reviews with more positive sentiment, we want to try and have a set of prompts that can produce varying kinds of sentiments rather than just one kind of sentiment. This set of prompts essentially forms our "observation space" and all completions are "actions", if our observation space contains primarily positive sentiment the model will not update heavily and will potentially still output negative sentiment when a prompt heavily favors it. Ideally we want our set of prompts to have a mix of sentiments.
# 
# We want to collect the first few (3-5, the choice is yours) words from each review to serve as prompts for our finetuned model. The generated text from these prompts will be later used to evaluate the performance of our finetuned model.
# 
# Emphasis - **we want to capture these prompts straight from the imdb dataset rather than write them ourselves.**

# In[25]:


def generate_prompts(dataset) -> List[str]:
    """Generate & return prompts from dataset."""
    prompts = [" ".join(review.split()[:4]) for review in dataset["text"]]
    return prompts



prompts = generate_prompts(imdb)
prompts[:15]


# <details>
# <summary>Solution</summary>
# 
# 
# ```python
# def generate_prompts(dataset):
#     """Generate & return prompts from dataset."""
#     prompts = [" ".join(review.split()[:4]) for review in dataset["text"]]
#     return prompts
# ```
# </details>
# 
# 
# ## GPT2-IMDB
# 
# The model that we will perform RLHF on is a GPT-2 model fine-tuned on the IMDB dataset, which can be found here: https://huggingface.co/lvwerra/gpt2-imdb. Since this model is finetuned on the IMDB dataset, the distribution of sentiments of its generations will be close to the distribution of sentiments of the original dataset. This means that after fine-tuning, the responses that are categorized as "nice" tend to lean towards being positive movie reviews rather than just generically positive continuations.
# 
# 
# ### Exercise - Load the GPT-2 model and generate reviews from prompts
# 
# ```c
# Difficulty: 🟠🟠🟠⚪⚪
# Importance: 🟠🟠🟠⚪⚪
# 
# You should spend up to 10-25 minutes on this exercise.
# ```
# 
# You will need to use the `AutoTokenizer` and `AutoModelForCausalLM` from the transformers package. You might want to use the `generate` method of the GPT-2 model that you load, if you do you should set the `max_new_tokens` argument to something that's large enough.
# 
# Play around with generating completions from this prompt and verify whether the completions approximately fit your initial expectations of the sentiments that the model would output.
# 
# **Note** - when you run `tokenizer(prompt)`, this will return a dictionary containing things like `token_ids` as well as a couple of other things that need to be passed into the model in a forward pass (e.g. a tensor indicating where you should mask `[PAD]` tokens). The best way to deal with this is to take `inputs = tokenizer(prompt)` and run `model.generate(**inputs)`.

# In[27]:


def generate_completion(prompt: str, model, tokenizer) -> str:
    """
    Generates completions for the given prompt (in the form of a string).

    Remember to set the `do_sample=True` flag when you call `model.generate`.
    """

    inputs = tokenizer(prompt, return_tensors="pt")
    out = model.generate(**inputs, do_sample=True)
    return tokenizer.decode(out.squeeze())


# Load the tokenizer and model.
# You can find the name of the model and tokenizer at the documentation page: https://huggingface.co/lvwerra/gpt2-imdb.
gpt2_tokenizer = AutoTokenizer.from_pretrained("lvwerra/gpt2-imdb")
gpt2 = AutoModelForCausalLM.from_pretrained("lvwerra/gpt2-imdb")

generate_completion(prompts[0], gpt2, gpt2_tokenizer)


# <details>
# <summary>Solution</summary>
# 
# ```python
# def generate_completion(prompt: str, model, tokenizer) -> str:
#     """
#     Generates completions for the given prompt (in the form of a string).
# 
#     Remember to set the `do_sample=True` flag when you call `model.generate`.
#     """
# 
#     inputs = tokenizer(prompt, return_tensors="pt")
#     out_tokens = model.generate(**inputs, do_sample=True, max_new_tokens=64)
#     return tokenizer.decode(out.squeeze())
# 
# 
# # Load the tokenizer and model.
# # You can find the name of the model and tokenizer at the documentation page: https://huggingface.co/lvwerra/gpt2-imdb.
# gpt2_tokenizer = AutoTokenizer.from_pretrained("lvwerra/gpt2-imdb")
# gpt2 = AutoModelForCausalLM.from_pretrained("lvwerra/gpt2-imdb")
# ```
# </details>
# 
# 
# ### The reward function
# 
# Judging by the name of this chapter you might think that you would be providing the reward function yourself but sadly we will not be doing this. Instead, we will be using a language model trained to perform sentiment analysis to generate the sentiment score (higher is positive). The language model we will be using to generate sentiment scores can be found here: https://huggingface.co/lvwerra/distilbert-imdb.
# 
# 
# #### Exercise - Get sentiment scores for a review
# 
# ```c
# Difficulty: 🟠🟠🟠🟠⚪
# Importance: 🟠🟠🟠⚪⚪
# 
# You should spend up to 15-30 minutes on this exercise.
# ```
# 
# We can use the model mentioned above in eval mode to generate sentiment scores and then transform the sentiments into rewards to be fed into the RLHF training loop.
# 
# Note: Here you should use `AutoModelForSequenceClassification` instead of `AutoModelForCausalLM` since we are doing classification (what's the sentiment?) rather than generation. Do not hesitate to print the objects, shapes and types of the variable you're working with.

# In[37]:


bert_imdb = AutoModelForSequenceClassification.from_pretrained("lvwerra/distilbert-imdb")
bert_imdb_tokenizer = AutoTokenizer.from_pretrained("lvwerra/distilbert-imdb")

@torch.inference_mode()  # Tell PyTorch to not build a computation graph and a few other things, for speed
def reward_model(samples: List[str], model=bert_imdb, tokenizer=bert_imdb_tokenizer, **kwargs) -> List[float]:
    """
    Returns the rewards for the given samples.

    kwargs are passed to your model during a forward pass.
    """
    # Make sure we're in eval mode
    model.eval()

    #input_ids = tokenizer(samples, return_tensors="pt")
    input_ids = tokenizer(samples, padding=True, truncation=True, return_tensors="pt")
    # Get top predictions at all the places we masked
    #print(input_ids)
    out = model(**input_ids, **kwargs)



    logits = out['logits']
    probabilities = torch.softmax(logits, dim=-1)
    tops = probabilities.to
    preds = out[input_ids == tokenizer.mask_token_id]

    return [[tokenizer.decode(t) for t in mask] for mask in tops]



# <details>
# <summary>Solution</summary>
# 
# 
# ```python
# bert_imdb = AutoModelForSequenceClassification.from_pretrained("lvwerra/distilbert-imdb")
# bert_imdb_tokenizer = AutoTokenizer.from_pretrained("lvwerra/distilbert-imdb")
# 
# @torch.inference_mode()  # Tell PyTorch to not build a computation graph and a few other things, for speed
# def reward_model(samples: List[str], model=bert_imdb, tokenizer=bert_imdb_tokenizer, **kwargs) -> List[float]:
#     """
#     Returns the rewards for the given samples.
# 
#     kwargs are passed to your model during a forward pass.
#     """
# 
#     inputs = tokenizer(samples, padding=True, truncation=True, return_tensors="pt")
# 
#     outputs = model(**inputs, **kwargs)
# 
#     logits = outputs.logits
#     probabilities = torch.softmax(logits, dim=1)
# 
#     # 1 is the index of the positive class
#     return probabilities[:, 1].tolist()
# ```
# </details>
# 
# 
# Test your reward model on some example prompts. Do the numbers make sense?

# In[38]:


example_prompts = ["Example string", "I'm having a good day", "You are an ugly person"]
rewards = reward_model(example_prompts)

for prompt, reward in zip(example_prompts, rewards):
    print(f"{prompt}: {reward}")

# Should be around 0.54, 0.97 and 0.05


# ### Exercise - Output sentiment scores using Huggingface pipelines
# 
# This is an alternate way to get a reward model working directly using Huggingface pipelines. This will enable you to use a diverse range of models quite easily by changing a couple of arguments and provide you with more functionality than the vanilla PyTorch loop you implemented above. Reading the relevant documentation is the key to success here.
# 
# **Part A: Create a huggingface pipeline to output sentiment scores for a generated review**
# 
# ```c
# Difficulty: 🟠🟠🟠⚪⚪
# Importance: 🟠🟠🟠🟠⚪
# 
# You should spend up to 10-25 minutes on this exercise.
# ```
# 
# Pipelines are a high-level way to use huggingface models for inference. Since the model that acts as our reward function will be used strictly for inference, it makes sense to wrap it in a pipeline.
# 
# The huggingface Pipeline documentation can be found here: [https://huggingface.co/docs/transformers/main_classes/pipelines](https://huggingface.co/docs/transformers/main_classes/pipelines).
# 
# You will need to set the `top_k` argument to the number of labels we expect the pipeline to return, in our case this would be 2 (Positive and Negative).
# 
# We would ideally also want to use the truncation flag and the batch_size argument to enable faster generation. For this exercise, these two things are not essential but could be experimented with as we will need these for later exercises.
# 

# In[ ]:


def create_pipeline(model_path):
    # Ensure we use a GPU if available
    if torch.cuda.is_available():
        device = int(os.environ.get("LOCAL_RANK", 0))
    else:
        device = -1

    return pipeline(
        "text-classification",
        model_path,
        top_k=2,
        truncation=True,
        batch_size=256,
        device=device,
    )


sentiment_fn = create_pipeline("lvwerra/distilbert-imdb")

sentiment_fn("What does the pipeline returns?")


# <details>
# <summary>Solution</summary>
# 
# 
# ```python
# def create_pipeline(model_path):
#     # Ensure we use a GPU if available
#     if torch.cuda.is_available():
#         device = int(os.environ.get("LOCAL_RANK", 0))
#     else:
#         device = -1
# 
#     return pipeline(
#         "text-classification",
#         model_path,
#         top_k=2,
#         truncation=True,
#         batch_size=256,
#         device=device,
#     )
# ```
# </details>
# 
# 
# **Part B: Map the sentiment pipeline to a reward function**
# 
# ```c
# Difficulty: 🟠🟠🟠⚪⚪
# Importance: 🟠🟠🟠🟠⚪
# 
# You should spend up to 10-20 minutes on this exercise.
# ```
# 
# We want the reward function to return a single number corresponding to the value of the positive label (the label we care about initially) for that generation rather than a dictionary containing the labels and their respective values (this is what the pipeline outputs, print it!).
# 

# In[ ]:


def reward_model(samples: List[str], **kwargs) -> List[float]:
    """
    Returns a list of reward values corresponding to the samples in `samples`.
    """
    ...


example_prompts = ["Example string", "I'm having a good day", "You are an ugly person"]
rewards = reward_model(example_prompts)

for prompt, reward in zip(example_prompts, rewards):
    print(f"{prompt}: {reward}")

# Should still be around 0.54, 0.97 and 0.046


# 
# <details>
# <summary>Solution</summary>
# 
# 
# ```python
# def reward_model(samples: List[str], **kwargs) -> List[float]:
#     """
#     Returns a list of reward values corresponding to the samples in `samples`.
#     """
# 
#     # This is one way of doing it, but there are many others.
#     return [
#         result['score']
#         for results in sentiment_fn(samples)
#         for result in results
#         if result['label'] == "POSITIVE"
#     ]
# ```
# </details>
# 
# 
# ### Exercise - Sentiment playground
# 
# ```c
# Difficulty: 🟠⚪⚪⚪⚪
# Importance: 🟠🟠🟠🟠⚪
# 
# You should spend up to 10-15 minutes on this exercise.
# ```
# 
# The reward model is now ready and you should take some time to feed in sentences of varying sentiments to check whether the rewards are as you expect. Remember the reward model is also a trained model so it exhibits all the quirks of one such as weird failure modes and potential to be broken with adversarial examples.
# 
# What are the most counterintuitive results you can find? **It's vitally important for the overall experience of the exercises today that you post your findings in the Signal chat.**
# 
# We will also be using this opportunity to test whether your reward model is set up correctly.

# In[ ]:


## Code below has an interesting set of examples:

prompts = [
    "I want to eat",
    "I want your puppy",
    "I want to eat your puppy",
]

for prompt in prompts:
    print(prompt, reward_model(prompt))


# 
# # 2️⃣ Using RLHF for Finetuning
# 
# 
# 
# > ##### Learning objectives
# >
# > - Learn about TRLX and how it can be used
# > - Use RLHF to improve sentiment of GPT2-produced movie reviews
# 
# 
# ## TRLX
# 
# 
# ### What is TRLX?
# 
# trlX is a library made for training large language models using reinforcement learning. It currently supports training using PPO or [ILQL](https://arxiv.org/abs/2206.11871) for models up to 20B using Accelerate.
# 
# In practice, RLHF with trlX is very easy if you already have a reward model and pretrained model.
# 
# ### Using trLX
# 
# Using trLX, we need to choose:
# 
# - Training Config
# - A prompt dataset.
# - A reward function (which makes use of the reward model).
# - Evaluation Prompts
# 
# These 4 objects are inputs to the train function which has already been imported for you.
# 
# 
# #### Training Config
# 
# See below for a config that when fed into TRLX performs RLHF using PPO, all hyperparameters are set to enable training and are best left untouched for the next exercise. You might want to increase max_new_tokens to get longer generations on your evaluation prompts during finetuning.
# 
# Increasing max_new_tokens will increase training time. For reference, keeping everything else the same in the config below and changing max_new_tokens from 40 to 100 increases finetuning time from ~26 mins to ~1h assuming the number of epochs and steps stay the same as the default. Picking a max_new_tokens value somewhere in the middle would be the best.
# 
# The model keyword specifies which model will be finetuned and we will be using the same GPT2 model that we used before to generate initial prompt completions.

# In[ ]:


def ppo_config():
    return TRLConfig(
        train=TrainConfig(
            seq_length=1024,
            epochs=100,
            total_steps=10000,
            batch_size=32,
            checkpoint_interval=10000,
            eval_interval=100,
            pipeline="PromptPipeline",
            trainer="AcceleratePPOTrainer",
        ),
        model=ModelConfig(model_path="lvwerra/gpt2-imdb", num_layers_unfrozen=2),
        tokenizer=TokenizerConfig(tokenizer_path="gpt2", truncation_side="right"),
        optimizer=OptimizerConfig(
            name="adamw",
            kwargs=dict(lr=3e-5, betas=(0.9, 0.95), eps=1.0e-8, weight_decay=1.0e-6),
        ),
        scheduler=SchedulerConfig(name="cosine_annealing", kwargs=dict(T_max=1e12, eta_min=3e-5)),
        method=PPOConfig(
            name="PPOConfig",
            num_rollouts=128,
            chunk_size=128,
            ppo_epochs=4,
            init_kl_coef=0.001,
            target=None,
            horizon=10000,
            gamma=1,
            lam=0.95,
            cliprange=0.2,
            cliprange_value=0.2,
            vf_coef=1,
            scale_reward="ignored",
            ref_mean=None,
            ref_std=None,
            cliprange_reward=10,
            gen_kwargs=dict(
                max_new_tokens=40,
                top_k=0,
                top_p=1.0,
                do_sample=True,
            ),
        ),
    )


# #### Prompt Dataset
# 
# The prompt dataset is the dataset that we'll use to generate reviews from the model specified in the config. These generations will be then be scored by the chosen reward function, this score will be used as the reward that will steer PPO to update the weights of the model towards maximising the reward function. As mentioned before the prompt dataset also forms the observation space for the PPO algorithm.
# 
# #### Reward Function
# 
# The reward function provides rewards given a set of prompt completions. In this particular case, the rewards will correspond with the positive sentiment of the completions and will steer the model towards generating strings that are generally positive .
# 
# #### Evaluation Prompts
# 
# The evaluation prompts are a set of prompts that we will use to validate the training process and the completions from these prompts will provide an indication of whether the overall sentiment is trending upwards.
# 
# Use a diversity of prompts to see how the completions evolve over time. Try to have at least 10.

# In this particular prompt, the initial prompt choice will cause the eval reward curve to have different starting points and end states.
# 
# 
# ## Exercise: Putting it all together - Reinforcing *positive* sentiment
# 
# ```c
# Difficulty: 🟠🟠🟠⚪⚪
# Importance: 🟠🟠🟠🟠⚪
# 
# You should spend up to 10-20 minutes on this exercise.
# ```
# 
# We will now be calling the train funcation and pass in the arguments as we've
# described above. The train function has already been imported for you and should
# be called like so:
# 
# All that you need to do below is fill in these four arguments in the main
# function. Make sure you understand what the significance of all four of these
# arguments is before moving on.

# In[ ]:


gc.collect()
torch.cuda.empty_cache()

# Call the train function with appropriate arguments
trainer = train(
    reward_fn=...,
    prompts=...,
    eval_prompts=...,
    config=...,
)

trainer.model.base_model.save_pretrained('rlhf-model')


# 
# <details>
# <summary>Solution</summary>
# 
# 
# ```python
# def main() -> None:
#     # Call the `train` function with appropriate arguments
#     trainer = train(
#         reward_fn = reward_model,
#         prompts = prompts,
#         eval_prompts = ['In my opinion'] * 10, ## Feel free to try different prompts
#         config =  ppo_config()
#     )
#     # You can save trainer here if you want, using trainer.save_pretrained("path/to/save")
# ```
# </details>
# 
# 
# Notice that we call `torch.cuda.empty_cache()` here, which is essential to free up GPU memory that might be held up as remnants of completed GPU operations or past failed runs. Running out of memory might be a common issue that you run in and running `torch.cuda.empty_cache()` will help you not get stuck as much. There are times when this is insufficient and you might need to restart the kernel to free up memory, you can call `nvidia-smi` on your terminal to see how much GPU memory is currently being used, and you can run `watch -n 1 nvidia-smi` to constantly keep an eye on GPU utilisation & available memory. Jupyter is unfortunately quite opaque in terms of memory management and you might need to call `torch.cuda.empty_cache()` and `gc.collect()` more often than you would expect.
# 
# TRLX logs to W&B and you should be prompted to add in your W&B key at some point. Take a look at the reward graph that shows the change in reward received by completions from the eval_prompts over the course of the training run. All the prompt completions are stored in the files section under the media folder.
# 
# 
# ## Exercise: Sentiment playground - Post RLHF
# 
# ```c
# Difficulty: 🟠⚪⚪⚪⚪
# Importance: 🟠🟠🟠🟠⚪
# 
# You should spend up to ~10 minutes on this exercise.
# ```
# 
# Try out your RLHF'd model!
# 

# In[ ]:


generate_completion("I hate this", trainer, gpt2_tokenizer)

