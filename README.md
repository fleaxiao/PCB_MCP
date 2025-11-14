# *BOOST*: A Knowledge-Driven Agentic LLM Paradigm for Power Electronic PCB Design

Official implementation for "*BOOST*: A Knowledge-Driven Agentic LLM Paradigm for Power Electronic PCB Design". Leveraging Board-Oriented Optimization and Semantic Technology (BOOST), this project presents a dedicated baseline agentic LLM workflow for power electronic PCB design, effectively overcoming the long-standing multiphysics optimization challenges in engineering practice.

## ✨ Highlights
- **AI-Driven Design**: Leverages LLM agents to automate and optimize PCB layout workflows
- **Knowledge Integration**: Incorporates IC datasheets, design rules, and layout guidelines
- **KiCAD Integration**: Seamlessly works with KiCAD PCB files for analysis and modification
- **Power Electronics Focus**: Specialized tools for high-frequency switching converters and power management circuits
- **Automated DRC**: Intelligent design rule checking with customizable clearance constraints
- **Datasheet Intelligence**: Automatically extracts pin configurations, layout recommendations, and component specifications


## 🧩 Setup Guideline
```bash
$env:PATH = "C:\kicad\bin;" + $env:PATH
```

python --version; python -c "import sys; print('Python Path:', sys.executable)"

python -m pip install <package-name> "mcp[cli]"

## 🙏 Acknowledgments

Built with:
- [KiCAD](https://www.kicad.org/) - Open-source PCB design software
- [Anthropic MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [Claude AI](https://www.anthropic.com/) - AI assistant integration


## ☎️ Contact
If you have any questions, please contact the authors at x.yang2@tue.nl

## ©️ License
This work is licensed under the MIT License.