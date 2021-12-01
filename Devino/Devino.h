/*
  Devino.h - Library for debugging/developing Arduino code.
  Created by Bryton Flecler.
*/

#ifndef Devino_h
#define Devino_h

#include "Arduino.h"

class Devino {
  public:
    Devino(bool commandsEnabled);
    uint16_t readAnalog(uint8_t pin);
    uint8_t readDigital(uint8_t pin);
    void writeAnalog(uint8_t pin, uint8_t val);
    void writeDigital(uint8_t pin, uint8_t val);
      void processCommands(void);
  private:
    bool _commandsEnabled;
    void runCommand(char* cmdLn);
};

struct Command {
  char* fn;
  char* arg1;
  char* arg2;
  char* arg3;
  char* arg4;
};

#endif
