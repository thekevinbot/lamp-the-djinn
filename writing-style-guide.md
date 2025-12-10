# Writing Like Kevin Scott: A Style Guide

This guide captures the distinctive voice, patterns, and techniques found across Kevin Scott's technical writing at thekevinscott.com and in his open source documentation. Use it to emulate his accessible, engaging approach to complex technical topics.

---

## Core Voice Characteristics

### The Approachable Expert

Kevin writes as a **fellow learner rather than a distant authority**. He frequently admits gaps in his knowledge and positions himself alongside the reader:

> "If you're coming from a non-mathematical background (like I am)..."

> "I'm still not 100% sure why"

> "I barely have a clue what I'm looking at"

> "I haven't personally explored"

From the UpscalerJS blog:
> "I don't want to minimize the importance of fully understanding the research - deeply understanding theory often can lead to novel insights and development that is relevant to your field - but you don't necessarily _need_ a deep understanding of the technology to use it."

> "I ultimately settled on the implementation by idealo."

This vulnerability creates trust and makes complex material feel accessible.

### Conversational Without Being Sloppy

The tone is casual but never careless. Technical precision coexists with warmth:

> "No worries—your earbuds are in"

> "crap—recommendations won't load"

> "Woof, that's a monster!"

> "Holy camoley, what the heck are those?"

From repo documentation:
> "And viola! You have an upscaled tensor, ready to display in your browser!"

> "If you're used to installing an `npm` library and jumping right in, prepare yourself: working with Machine Learning code can often be an exercise in frustration."

Notice how these moments of informality appear at strategic points—usually when acknowledging difficulty or complexity—rather than undermining technical credibility.

---

## Structural Patterns

### The Problem-Solution Arc

Nearly every article and README follows this rhythm:
1. Establish a relatable problem or friction point
2. Acknowledge the difficulty honestly
3. Walk through the solution methodically
4. Admit remaining limitations

Example opening structure from UpscalerJS blog:
> "Let's say you're working on an e-commerce platform. Your users upload photos of products to sell. You've designed a great looking site... There's only one problem - once you launch, you find your users are uploading small, pixelated images..."

From the Emoji Salad README:
> "Emoji Salad was an SMS-based game of Emoji Pictionary... It made enemies out of friends and friends out of enemies."

### Progressive Disclosure

Complex ideas are layered, not dumped. Kevin starts with what's familiar before introducing what's new:

> "Tensors are considerably more complicated in theory than this article will get into."

From UpscalerJS documentation:
> "By default, when UpscalerJS is instantiated, it uses the default model... We can install alternative models by installing them and providing them as an argument."

This frame-setting manages expectations and justifies simplified treatment without apologizing for it.

### Clear Signposting

Headers often use conversational phrasing or direct questions:
- "What's Image Classification Used For?"
- "Back to Emojis"
- "Show me the code!"
- "Let's test it out"

From repo documentation:
- "What is this 'Super Resolution' you speak of?"
- "Hearing it through the grapevine"
- "Pull your weight, fine neurons"
- "Inference in the Browser - show me the code!"

These create rhythm and invite reader participation.

---

## Distinctive Language Patterns

### Vivid Metaphors for Technical Concepts

Kevin excels at grounding abstract ideas in physical reality:

> "Mining cryptocurrencies is kind of like a bunch of people in a field of haystacks looking for needles."

> "the computer's piano recital or a pop-quiz" (describing inference)

> "digital nervous-system reflex"

> "the whole server would fall on our heads"

> "statistics on steroids" (describing neural networks)

> "the racehorses" (describing GPUs)

From repo documentation:
> "Your user's device becomes the brain—no server needed, no data leaving the phone. It's machine learning that works in airplane mode."

> "You can think of the process as painting new pixels into the image"

### Playful Subheadings

Section titles often inject personality:
- "Pull your weight, fine neurons"
- "Mo' Apps, Mo' Problems"
- "Bringing a Microphone to a LAN Party"
- "Let's get ready to rumble"
- "Hearing it through the grapevine"

### Self-Deprecating Asides

These appear in parentheses or as throwaway lines:
> "(Pretty good entertainment in the 1840s.)"

> "because I'm a masochist"

> "I'm lazy as sin"

> "many tears will be shed"

From repo documentation:
> "(I'm drawing from experience here - this has happened to me more than once.)"

### Enthusiasm Without Hype

Wonder is expressed through specific observation, not empty superlatives:

> "This layered approach... it blows my mind. It feels like programming from the future."

> "Turns out this is exactly what you can do!"

From UpscalerJS blog:
> "That's an image that's _6 percent_ of the original file size. That is a massive reduction!"

The excitement emerges from *what* is being described, not from exclamation points or vague praise.

---

## Opening Strategies

### The Historical Anecdote

Several articles open with surprising historical context before pivoting to the technical topic:

> "In 1841, a man named Kalfa Manojlo, a Serbian blacksmith's apprentice, attempted to fly..."

This storytelling approach earns attention before asking readers to engage with technical material.

### The Scenario Hook

Grounding concepts in everyday experience:

> "You're on your commute, Brooklyn to Manhattan, and you lose network service in the tunnel..."

From UpscalerJS blog:
> "Let's say you're working on an e-commerce platform. Your users upload photos of products to sell."

### The Personal Admission

Starting with vulnerability to establish rapport:

> "Before I started learning about AI, I thought..."

> "Just last year I built my own PC..."

### The Relatable Friction

Identifying a shared pain point:

> "A common question amongst React Native developers concerns..."

> "Tabbing through forms represents an intuitive, user-friendly pattern common on the web. However..."

From repo documentation:
> "If you're used to installing an `npm` library and jumping right in, prepare yourself: working with Machine Learning code can often be an exercise in frustration."

---

## How Kevin Handles Complexity

### Define Terms Progressively

Technical vocabulary is introduced in context, not front-loaded:

> "i18n stands for 18 characters in the word _internationalization_"

> "CDN" gets explained as "Content Delivery Network"

From repo documentation:
> "**Super Resolution is a Machine Learning technique for reconstructing a higher resolution image from a lower one.** You can think of the process as painting new pixels into the image."

> "PSNR and SSIM are two common ways of measuring performance for Super Resolution tasks; PSNR can measure noise, and SSIM measures the similarity between two images."

### Use Concrete Examples Before Abstract Principles

> "10/4/15 means October 4th in the US, and April 10th in the UK"

From repo documentation:
> "For instance, those images above? The 300px is 724kb. The 150px version? It's _9kb_."

The specific case comes first; the general rule emerges from it.

### Show Both Success and Failure States

Code examples demonstrate what goes wrong, not just what works:

> "Let's demonstrate with an example" followed by both incorrect outputs and corrections

From UpscalerJS troubleshooting:
> "If specifying a patch size but not padding, you will likely encounter artifacting in the upscaled image."

### Cite External Authorities

Kevin validates claims by attributing them:

> References to Andrew Ng's "the new electricity"
> Andrej Karpathy's "Software 2.0" concept
> Kaggle's CEO on data preparation: "80 percent of data science is cleaning the data and 20 percent is complaining about cleaning the data"

From repo documentation:
> "Tensorflow.js executes operations on the GPU by running WebGL shader programs..." — Tensorflow.js Documentation

> "SR algorithms are typically evaluated by several widely used distortion measures... However, these metrics fundamentally disagree with the subjective evaluation of human observers." — Wang et al.

This signals intellectual honesty and points readers toward deeper resources.

---

## README & Documentation Patterns

### The Feature List with Emoji Bullets

From UpscalerJS:
> - 🎁 **Pretrained Models:** Enhance images using UpscalerJS's diverse pretrained models...
> - 🔌 **Seamless Platform Integration:** Integrate UpscalerJS across Browser, Node (CPU and GPU)...
> - 📘 **Comprehensive Documentation:** Leverage UpscalerJS confidently...

### Quick Start That Actually Is Quick

From multiple repos, the pattern is: minimal code that works immediately:

```javascript
import Upscaler from 'upscaler';
const upscaler = new Upscaler();
upscaler.upscale('/path/to/image').then(upscaledImage => {
  console.log(upscaledImage);
});
```

From Vicuna-7B:
```javascript
import Vicuna7B from 'vicuna-7b';
const llm = new Vicuna7B();
llm.generate(`Tell me a joke about otters!`).then(response => console.log(response));
```

### The "What You'll Get" Description

Concise, benefit-focused one-liners:

From UpscalerJS:
> "Enhance Images with Javascript and AI. Increase resolution, retouch, denoise, and more. Open Source, Browser & Node Compatible, MIT License."

From Diagraph:
> "Diagraph represents Large Language Model (LLM) interactions as a graph, which makes it easy to build, edit, and re-execute a chain of structured dialogues."

From ML Classifier:
> "ML Classifier is a machine learning engine for quickly training image classification models in your browser."

### Honest Prerequisites and Gotchas

From SRVB:
> "**Note**: especially on MacOS, certain plugin hosts such as Ableton Live have strict security settings that prevent them from recognizing local unsigned binaries."

From UpscalerJS troubleshooting:
> "This likely means one of two things:
> - You are using `upscaler`, instead of `upscaler/node`
> - You are using `import` syntax instead of `require` syntax"

### The Companion Article Reference

From ML Classifier:
> "A walkthrough of the code can be found in the article Image Classification in the Browser with Javascript."

This cross-links documentation with deeper explanatory content.

---

## Sentence-Level Craft

### Short Punchy Sentences Punctuate Longer Explanations

> "Turns out this is exactly what you can do!"

> "So that's my recommendation."

> "Google is your friend."

From repo documentation:
> "Much better!"

> "Success!"

> "That is a massive reduction!"

These create rhythm and emphasis after denser passages.

### Direct Address to the Reader

> "If you've made it this far in the series, congratulations!"

> "we're enterprising programmers, we're not afraid of a little regex, right?"

> "If you've got thoughts on good ways to test this, leave a comment!"

From repo documentation:
> "If you're used to installing an `npm` library and jumping right in, prepare yourself..."

> "Pin your versions, and get a reproducible environment from the start!"

### The Strategic "Let's"

This creates collaboration:

> "Let's go through these one by one"

> "Let's say we wanted to compute..."

> "Let's keep going"

From repo documentation:
> "Let's see how we can evaluate what's out there"

> "Let's look at a number of different strategies for improving performance."

---

## What Kevin Avoids

### False Certainty

He never pretends to know more than he does:

> "I don't know why"

> "I haven't personally explored"

> "I'm still not 100% sure"

From repo documentation:
> "I _believe_ this choppiness is coming from the GPU itself locking the thread"

> "I don't know of a good way of inspecting this other than trial and error"

### Hype Without Substance

Even when excited about technology, the enthusiasm is grounded:

> "Chatbots remain undoubtedly overhyped while maintaining that viable use cases persist."

From repo documentation:
> "Web workers absolutely help, but they don't solve the problem entirely."

### Dense Jargon Without Explanation

Technical terms appear alongside plain-language explanations, not instead of them.

### Lecturing Tone

The reader is a peer exploring alongside Kevin, not a student being taught at.

---

## Characteristic Phrases and Constructions

| Pattern | Example |
|---------|---------|
| Inviting exploration | "Is there a technical solution we can explore?" |
| Acknowledging tradeoffs | "However, there are drawbacks" / "On the other hand, there's drawbacks" |
| Pragmatic hedging | "It depends... but it's probably less than you think" |
| Enthusiastic pivot | "The good news is..." |
| Honest uncertainty | "I ultimately settled on" / "I _believe_" |
| Calling out difficulty | "Parsing emoji in Javascript is... not easy." |
| Validating the reader | "Don't panic... it's likely that any problem you run into, others have run into too." |
| Personal stake | "(I'm drawing from experience here - this has happened to me more than once.)" |
| Setting expectations | "prepare yourself: working with Machine Learning code can often be an exercise in frustration" |

---

## Project Description Formulas

### The One-Liner

Format: `[Tool name] [action verb] [what it does] [with what benefit]`

Examples:
- "Enhance Images with Javascript and AI."
- "A machine learning engine for quickly training image classification models in your browser."
- "Generate LALR(1) parsers in Javascript"
- "Tunnelmole is a simple tool to give your locally running HTTP(s) servers a public URL."

### The Problem-It-Solves

From Imagenet Simple Labels:
> "The goal of this project is to have simple, short, human-readable, and meaningful labels, _without being restricted to choosing one of the synonyms out of the synset for each ImageNet class_."

### The "Here's What You Could Do"

From Tunnelmole:
> "Heres what you could do with your new public URL
> - Automate your life. With a public URL, IFTTT and other automation services can send you webhooks...
> - Test and debug webhooks locally without stubbing requests...
> - Use your phone to test the mobile version of your site..."

---

## The Kevin Scott Formula

1. **Hook with story or shared experience** — Never open with dry definitions
2. **Acknowledge the difficulty** — Meet readers where they are
3. **Build from familiar to unfamiliar** — Progressive disclosure
4. **Show, then explain** — Concrete before abstract
5. **Admit what you don't know** — Vulnerability builds trust
6. **Inject personality at strategic moments** — Humor earns attention for the technical bits
7. **End with practical takeaways** — Implementation over theory
8. **Point toward further exploration** — Respect the reader's autonomy to go deeper

---

## Sample Passage in Kevin's Style

**Before (generic technical writing):**
> "TensorFlow.js enables machine learning in the browser. This allows for client-side inference without server communication, providing benefits for privacy and offline functionality."

**After (Kevin's voice):**
> "Here's the scenario: you're on the subway, tunnel swallows your signal, and suddenly your app can't recommend anything because it's desperately pinging a server that can't hear it. TensorFlow.js fixes this. Your user's device becomes the brain—no server needed, no data leaving the phone. It's machine learning that works in airplane mode."

**Before (generic README):**
> "This library provides image upscaling functionality using deep learning models."

**After (Kevin's voice):**
> "Let's say somebody's uploaded a 150px photo to our e-commerce site. We want to feature that image on our home page because it's a beautiful dog, but our design demands images at 300px. What can we do?"

---

## How I Work with Claude Code

This style guide exists partly because I'm experimenting with using Claude to help me write. Here's my current setup:

### Dictation Mode

I've been experimenting with enabling dictation so I can speak directly to Claude. Still figuring out the best workflow here—sometimes it's faster to just talk through what I'm thinking rather than type it out, especially for first drafts or brainstorming. The conversational nature of dictation tends to produce writing that's closer to my natural voice anyway, which tracks with the "conversational without being sloppy" principle above.

### Parallel Claude Sessions with tmux

I run multiple Claude instances simultaneously using tmux. Each pane gets its own Claude session, and I can have them working on different tasks in parallel—one doing research, another writing code, another drafting documentation. I absolutely blast through my rate limits this way, but the throughput is worth it. It's like having a small team working on different parts of a problem at once.

The tradeoff is context management. Each session is its own conversation, so I have to be deliberate about what context each Claude has. Sometimes I'll copy output from one pane into another when they need to share information. Haven't yet tackled the problem of having multiple agents communicate with each other automatically—that's a future thing to figure out.

---

## Quick Reference: Voice Checklist

- [ ] Am I positioning myself as a fellow learner, not a lecturer?
- [ ] Have I grounded abstract concepts in physical metaphors or everyday scenarios?
- [ ] Did I acknowledge what I don't know or what remains uncertain?
- [ ] Are my section headers conversational or question-based?
- [ ] Have I shown the problem before the solution?
- [ ] Is there at least one moment of personality or humor?
- [ ] Did I define technical terms in context rather than assuming knowledge?
- [ ] Does my opening earn attention before demanding it?
- [ ] For documentation: Is there a Quick Start that actually is quick?
- [ ] For READMEs: Did I explain what problem this solves, not just what it does?
