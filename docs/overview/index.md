# Overview

Welcome to the QuickDev overview section. These pages explain the core concepts, philosophy, and architecture of QuickDev.

## Contents

**[Philosophy](philosophy.md)** - Understanding QuickDev's vision and approach

- Core principles of code generation over abstraction
- 12-Factor App alignment
- Target audience: VPS developers
- QuickDev site structure
- Evolution from the 1990s to today

**[Architecture](architecture.md)** - How QuickDev is structured

- Module organization (qdbase, qdcore, qdutils)
- XSynth preprocessor system
- Flask integration packages
- Bootstrapping architecture
- Database and configuration management

**[vs Frameworks](vs-frameworks.md)** - How QuickDev compares to other tools

- QuickDev vs Django/Flask/FastAPI
- QuickDev vs Docker/Kubernetes
- QuickDev vs Ansible/Chef/Puppet
- When to use QuickDev
- When to use alternatives

## Quick Summary

**QuickDev is not a framework** - it's a collection of idioms and code generation tools that work alongside Flask, Django, and other Python frameworks.

**Three core capabilities:**

1. **XSynth Preprocessor** - Generate Python from high-level declarations
2. **Reusable Idioms** - Pre-built packages (qdflask, qdimages, qdcomments)
3. **Site Management** - Standardized deployment structure for VPS nodes

**Target audience:** Developers managing their own servers who want:

- Simple deployment without Docker complexity
- Separation of secrets (.env) from configuration (YAML)
- Apache integration with automatic config generation
- Proven patterns refined over decades

Ready to dive deeper? Start with [Philosophy](philosophy.md) to understand the vision, then check out [Architecture](architecture.md) for technical details.
