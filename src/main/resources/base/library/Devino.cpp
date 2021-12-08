/*
  Devino.cpp - Library for debugging/developing Arduino code.
  Created by Bryton Flecker.
*/

#include "Arduino.h"
#include "Devino.h"

Devino::Devino(bool transmit) {
  _transmit = transmit;
}


void Devino::processCommands(void) {
  static boolean isCmd = false;
  static byte index = 0;
  
  char cmd[64];
  char startMarker = '<';
  char endMarker = '>';
  char byte_;

  while(Serial.available() > 0) {
    byte_ = Serial.read();

    if(isCmd == true) {
      if (byte_ != endMarker) {
        cmd[index] = byte_;
        index = constrain(index + 1, 0, 63);
      }
      else {
        cmd[index] = '\0'; // terminate the string
        isCmd = false;
        index = 0;
        this->runCommand(cmd);
        break;
      }
    }
    else if (byte_ == startMarker) {
      isCmd = true;
    }
  }
}


void Devino::runCommand(char* cmdLn) {
  Command cmd;

  cmd.fn = strtok(cmdLn, " ");
  for(uint8_t i = 1; i < 5; i++) {
    switch(i) {
      case 1:
        cmd.arg1 = strtok(NULL, " ");
        break;
      case 2:
        cmd.arg2 = strtok(NULL, " ");
        break;
      case 3:
        cmd.arg3 = strtok(NULL, " ");
        break;
      case 4:
        cmd.arg4 = strtok(NULL, " ");
        break;
      default:
        break;
    }
  }

  if(strcmp(cmd.fn, "set")==0) {
    if(strcmp(cmd.arg1, "a")==0) {
      analogWrite(atoi(cmd.arg2), atoi(cmd.arg3));
      _enabledPins[atoi(cmd.arg2)] = 0;
    }
    else if(strcmp(cmd.arg1, "d")==0) {
      digitalWrite(atoi(cmd.arg2), atoi(cmd.arg3));
      _enabledPins[atoi(cmd.arg2)] = 0;
    }
  }
  else if(strcmp(cmd.fn, "get")==0) {
    if(strcmp(cmd.arg1, "a")==0) {
      this->readAnalog(atoi(cmd.arg2));
      _enabledPins[atoi(cmd.arg2)] = 1;
    }
    else if(strcmp(cmd.arg1, "d")==0) {
      this->readDigital(atoi(cmd.arg2));
      _enabledPins[atoi(cmd.arg2)] = 1;
    }
  }
}


uint16_t Devino::readAnalog(uint8_t pin) {
  uint16_t val = analogRead(pin);

  if(_transmit) {
    char buffer[32];
    sprintf(buffer, "<RA%d %u>", pin, val);
    Serial.println(buffer);
  }

  return val;
}


uint8_t Devino::readDigital(uint8_t pin) {
  uint8_t val = digitalRead(pin);
  
  if(_transmit) {
    char buffer[32];
    sprintf(buffer, "<RD%d %d>", pin, val);
    Serial.println(buffer);
  }

  return val;
}


void Devino::writeAnalog(uint8_t pin, uint8_t val) {
  if(_enabledPins[pin] == 1) {
    analogWrite(pin, val);
    
    if(_transmit) {
      char buffer[32];
      sprintf(buffer, "<WA%d %d>", pin, val);
      Serial.println(buffer);
    }
  }
}


void Devino::writeDigital(uint8_t pin, uint8_t val) {
  if(_enabledPins[pin] == 1) {
    digitalWrite(pin, val);
    
    if(_transmit) {
      char buffer[32];
      sprintf(buffer, "<WD%d %d>", pin, val);
      Serial.println(buffer);
    }
  }
}
