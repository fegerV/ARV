// pages/Projects/ARContent/WizardSteps.tsx
import React from 'react';
import { 
  Box, 
  Stepper, 
  Step, 
  StepLabel 
} from '@mui/material';
import { useWizard } from './useWizard';
import { Step1Portrait } from './Step1Portrait';
import { Step2Marker } from './Step2Marker';
import { Step3Videos } from './Step3Videos';
import { Step4Schedule } from './Step4Schedule';
import { Step5QR } from './Step5QR';
import { StepComplete } from './StepComplete';

const steps = ['Портрет', 'Маркер', 'Видео', 'Расписание', 'QR-код', 'Готово'];

export const WizardSteps = () => {
  const { currentStep } = useWizard();

  const renderStep = () => {
    switch (currentStep) {
      case 0: return <Step1Portrait />;
      case 1: return <Step2Marker />;
      case 2: return <Step3Videos />;
      case 3: return <Step4Schedule />;
      case 4: return <Step5QR />;
      case 5: return <StepComplete />;
      default: return <Step1Portrait />;
    }
  };

  return (
    <Box sx={{ py: 4 }}>
      <Stepper activeStep={currentStep} sx={{ mb: 6 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      {renderStep()}
    </Box>
  );
};