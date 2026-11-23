---
name: consult-opus
description: Answer one narrow design question without editing files.
argument-hint: "<single design question and relevant paths>"
context: fork
agent: opus-consultant
background: false
disable-model-invocation: true
---
Your task is $ARGUMENTS. Inspect only the context needed to answer this single design question. Return a recommendation and its key trade-offs in 300 words or fewer, including any blocking question. Do not edit files.
