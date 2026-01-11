#!/bin/bash
###############################################################################
# LaTeX PDF Compilation Script for LEGOLAS ZnSSe Paper
#
# This script compiles $1.tex into a PDF
# Requires: LaTeX installation (BasicTeX or MacTeX)
###############################################################################

# Note: Not using 'set -e' because pdflatex returns non-zero for warnings too
# We check for actual errors by verifying PDF output exists

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}LEGOLAS ZnSSe Paper - PDF Compilation${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Change to paper directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}Working directory:${NC} $SCRIPT_DIR\n"

# Check if LaTeX is installed (check common locations)
PDFLATEX=""
if command -v pdflatex &> /dev/null; then
    PDFLATEX="pdflatex"
elif [ -x "/Library/TeX/texbin/pdflatex" ]; then
    PDFLATEX="/Library/TeX/texbin/pdflatex"
elif [ -x "/usr/local/texlive/2025basic/bin/universal-darwin/pdflatex" ]; then
    PDFLATEX="/usr/local/texlive/2025basic/bin/universal-darwin/pdflatex"
fi

if [ -z "$PDFLATEX" ]; then
    echo -e "${RED}ERROR: pdflatex not found!${NC}\n"
    echo -e "LaTeX is not installed. Please install it first:\n"
    echo -e "${YELLOW}Option 1 - BasicTeX (smaller, ~100MB):${NC}"
    echo -e "  brew install --cask basictex"
    echo -e "  eval \"\$(/usr/libexec/path_helper)\"\n"
    echo -e "${YELLOW}Option 2 - Full MacTeX (~4GB):${NC}"
    echo -e "  brew install --cask mactex"
    echo -e "  eval \"\$(/usr/libexec/path_helper)\"\n"
    echo -e "${YELLOW}Option 3 - Use Overleaf (online, no installation):${NC}"
    echo -e "  https://www.overleaf.com/\n"
    exit 1
fi

echo -e "${GREEN}✓${NC} pdflatex found: $PDFLATEX\n"

# Check if main LaTeX file exists
if [ ! -f "$1.tex" ]; then
    echo -e "${RED}ERROR: $1.tex not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Source file: $1.tex found\n"

# Check if figures directory exists
if [ ! -d "figures" ]; then
    echo -e "${YELLOW}WARNING: figures/ directory not found!${NC}"
    echo -e "Some figures may be missing in the output.\n"
else
    echo -e "${GREEN}✓${NC} Figures directory found\n"
    echo -e "Available figures:"
    ls -1 figures/*.pdf figures/*.png figures/*.jpg 2>/dev/null | sed 's/^/  - /' || echo "  (none)"
    echo ""
fi

# Clean up old compilation files
echo -e "${YELLOW}Cleaning up old compilation files...${NC}"
rm -f $1.aux $1.log $1.out $1.toc $1.pdf
echo -e "${GREEN}✓${NC} Cleanup complete\n"

# First compilation pass
echo -e "${YELLOW}Running pdflatex (1st pass)...${NC}"
$PDFLATEX -interaction=nonstopmode $1.tex > /dev/null 2>&1
# Check if PDF was created (pdflatex may return non-zero for warnings)
if [ ! -f "$1.pdf" ] && ! grep -q "Output written" $1.log 2>/dev/null; then
    echo -e "${RED}ERROR: First pdflatex pass failed!${NC}"
    echo -e "\nCheck the log file for details:"
    echo -e "  cat $1.log\n"
    echo -e "Last 20 lines of log:"
    tail -20 $1.log 2>/dev/null || echo "Log file not found"
    exit 1
fi
echo -e "${GREEN}✓${NC} First pass complete\n"

# Check if bibliography file exists and run bibtex if needed
if [ -f "$1.bib" ] || grep -q "\\bibliography" $1.tex 2>/dev/null; then
    echo -e "${YELLOW}Running bibtex...${NC}"
    bibtex $1 > /dev/null 2>&1 && echo -e "${GREEN}✓${NC} BibTeX complete\n" || {
        echo -e "${YELLOW}⚠${NC}  BibTeX not needed or failed (continuing...)\n"
    }
fi

# Second compilation pass (resolve references)
echo -e "${YELLOW}Running pdflatex (2nd pass)...${NC}"
$PDFLATEX -interaction=nonstopmode $1.tex > /dev/null 2>&1
# Check if PDF was created
if [ ! -f "$1.pdf" ]; then
    echo -e "${RED}ERROR: Second pdflatex pass failed!${NC}"
    echo -e "\nCheck the log file for details:"
    echo -e "  cat $1.log\n"
    exit 1
fi
echo -e "${GREEN}✓${NC} Second pass complete\n"

# Third compilation pass (ensure all references are resolved)
echo -e "${YELLOW}Running pdflatex (3rd pass)...${NC}"
$PDFLATEX -interaction=nonstopmode $1.tex > /dev/null 2>&1
# Check if PDF was created
if [ ! -f "$1.pdf" ]; then
    echo -e "${RED}ERROR: Third pdflatex pass failed!${NC}"
    echo -e "\nCheck the log file for details:"
    echo -e "  cat $1.log\n"
    exit 1
fi
echo -e "${GREEN}✓${NC} Third pass complete\n"

# Check if PDF was created
if [ -f "$1.pdf" ]; then
    PDF_SIZE=$(du -h $1.pdf | cut -f1)
    PDF_PAGES=$(pdfinfo $1.pdf 2>/dev/null | grep Pages | awk '{print $2}' || echo "?")

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ PDF COMPILATION SUCCESSFUL!${NC}"
    echo -e "${GREEN}========================================${NC}\n"

    echo -e "${BLUE}Output file:${NC}"
    echo -e "  📄 $1.pdf"
    echo -e "  📏 Size: ${PDF_SIZE}"
    echo -e "  📖 Pages: ${PDF_PAGES}\n"

    echo -e "${BLUE}Location:${NC}"
    echo -e "  $(pwd)/$1.pdf\n"

    echo -e "${YELLOW}To view the PDF:${NC}"
    echo -e "  open $1.pdf\n"

    echo -e "${YELLOW}To clean up auxiliary files:${NC}"
    echo -e "  rm -f $1.aux $1.log $1.out $1.toc\n"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ PDF COMPILATION FAILED!${NC}"
    echo -e "${RED}========================================${NC}\n"
    echo -e "The PDF file was not created. Check the log file:\n"
    echo -e "  cat $1.log\n"
    exit 1
fi
