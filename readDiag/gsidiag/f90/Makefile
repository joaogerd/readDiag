# fortran and fortran-to-python linker compiler
FC		:=	gfortran
F2PY	:=	f2py

# root directory for source code
# (relative to this one)
P       :=  $(shell pwd)
# @$(shell echo) $(P)
src	:=  $(WIM2D_PATH)/fortran/src
# @echo $(src)

# keep binaries here
bin := ../bin
lib := ../lib

# directory where objects are kept
# ODIR	:=	$(P)/objs
ODIR	:=	./objs

# directory where modules are put into
# MDIR	:=	$(P)/mods
MDIR	:=	./mods

# FCFLAGS=-O
# check for errors
FFLAGS=-fconvert=big-endian

# include modules/headers from $(MDIR) or $(HDIR)
IFLAGS=-I$(MDIR) -I.

# Put modules in $(MDIR) when they are created
OFLAGS=-J$(MDIR)


## ============================================================================
## run in double precision
## - export WIM2D_TYPE=single to use single precision;
##   leave undefined or set to double (for example) to use double precision
#ifneq ($(WIM2D_TYPE),single)
#	FCFLAGS += -fdefault-real-8 -fdefault-double-8
#endif
# ============================================================================

# Flags for f2py
F2PY_FLAGS=--fcompiler=$(FC) --f77flags="$(FFLAGS)" --f90flags="$(FFLAGS)"

# fortran program teste
# - executable called by run_WIM2d.sh
#   (cd ../run; ./run_WIM2d.sh)
PROG_F := $(ODIR)/DiagRead.o
TARG_F := DiagRead.x

# fortran interface program
# - NB f2py needs the full path

PROG_PY := $(src)/diag2python.f90
SIGN_PY := diag2python.pyf
TARG_PY := diag2python$(shell python3-config --extension-suffix)

#
# Sources and objects
#
SRCS := \
	m_string.f90    \
	ReadDiagMod.f90 \
	ReadDiagModRad.f90 \
	diag2python.f90

OBJS := \
	$(ODIR)/m_string.o    \
   $(ODIR)/ReadDiagMod.o \
   $(ODIR)/ReadDiagModRad.o \
	$(ODIR)/diag2python.o \
	$(ODIR)/DiagRead.o 

# Create objects by compiling their respective .F and/or .f90 files
# (add dependency on header files also, so we recompile if headers change)
$(ODIR)/%.o:	%.f90
	@mkdir -p $(ODIR) $(MDIR)
	$(FC) -c -o $@ $< $(FCFLAGS) $(IFLAGS) $(OFLAGS)
$(ODIR)/%.o:	%.F
	@mkdir -p $(ODIR) $(MDIR)
	$(FC) -c -o $@ $< $(FCFLAGS) $(IFLAGS) $(OFLAGS)

# Link objects to make executable $(TARGET_F)
# (default)
all:	py exec
	
exec: $(PROG_F) $(OBJS)
	@echo " "
	@mkdir -p $(bin)
	$(FC) -o $(TARG_F) $^ $(FCFLAGS) $(IFLAGS)
	mv $(TARG_F) $(bin)
	@echo " "

# Link objects to make python module $(TARG_PY)
py: $(SRCS)
	@echo " "
	@mkdir -p $(lib)
	$(F2PY) -c $(SIGN_PY) $^ $(F2PY_FLAGS)
	mv $(TARG_PY) $(lib)
	@echo " "




# DEPENDENCIES
$(ODIR)/m_string.o:	m_string.f90
$(ODIR)/DiagRead.o:	DiagRead.f90	$(ODIR)/ReadDiagMod.o 
$(ODIR)/diag2python.o:	diag2python.f90 $(ODIR)/ReadDiagMod.o	$(ODIR)/ReadDiagModRad.o
$(ODIR)/ReadDiagMod.o:	ReadDiagMod.f90 $(ODIR)/m_string.o
$(ODIR)/ReadDiagModRad.o:	ReadDiagModRad.f90 $(ODIR)/m_string.o

#
$(OBJ_MAIN):	$(OBJS)
$(PROG_PY):	$(OBJS)

.PHONY: clean vclean

# clean: keep executable, but delete modules and objects
clean:
	rm -fr $(ODIR)/*.o $(MDIR)/*.mod $(ODIR) $(MDIR)

# vclean: delete executable, and delete modules and objects
aclean:
	rm -fr $(ODIR)/*.o $(MDIR)/*.mod \
			 $(ODIR) $(MDIR)  \
			 $(bin) $(lib)    \
	   	 $(bin)/$(TARG_F) \
	   	 $(lib)/$(TARG_PY) 

# -I. include headers from "." directory;
# -L. include libraries from "." directory;
# $^ everything to the right of ":";
# $@ first on the left of ":";
# $< first on the right of ":";
# The .PHONY rule keeps make from doing something with a
# file named clean.

