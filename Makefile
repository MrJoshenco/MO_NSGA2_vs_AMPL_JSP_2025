# Makefile for compiling NSGA-II source code
# Updated for organized project structure

CC=gcc
LD=gcc
RM=rm -f

# Directories
SRC_DIR=src
BUILD_DIR=build

CFLAGS=-Wall -std=c99 -pedantic -g -I$(SRC_DIR)
LDFLAGS=-lm

# Source files and object files
SRCS=$(wildcard $(SRC_DIR)/*.c)
OBJS=$(patsubst $(SRC_DIR)/%.c,$(BUILD_DIR)/%.o,$(SRCS))

# Main executable
MAIN=$(BUILD_DIR)/nsga2r

.PHONY: all clean

all: $(BUILD_DIR) $(MAIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(MAIN): $(OBJS)
	$(LD) $(OBJS) -o $(MAIN) $(LDFLAGS)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c $(SRC_DIR)/global.h $(SRC_DIR)/rand.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	$(RM) $(OBJS) $(MAIN)

# Run target (example usage)
run: $(MAIN)
	@echo "Ejecutable ubicado en: $(MAIN)"
	@echo "Uso: $(MAIN) <seed> <input_file>"
