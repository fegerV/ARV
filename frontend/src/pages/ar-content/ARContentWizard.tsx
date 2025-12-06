// pages/ar-content/ARContentWizard.tsx
import React, { useState } from 'react';
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  Button,
  Typography,
  Paper,
  CircularProgress
} from '@mui/material';
import { Step1Portrait } from './Step1Portrait';
import { Step2Marker } from './Step2Marker';
import { Step3Videos } from './Step3Videos';
import { Step4Schedule } from './Step4Schedule';
import { Step5QR } from './Step5QR';
import { ARContentCreate, ARContent } from '../../types/ar-content';

const steps = ['Портрет', 'Маркер', 'Видео', 'Расписание', 'QR-код'];

export const ARContentWizard: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [arContent, setArContent] = useState<Partial<ARContent> & { project_id: number }>({
    project_id: 0, // This should be passed as a prop or from URL params
    title: '',
    videos: [],
  });

  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleFinish = () => {
    // Handle final submission
    console.log('AR Content created:', arContent);
  };

  const getStepContent = (step: number) => {
    switch (step) {
      case 0:
        return <Step1Portrait onNext={handleNext} />;
      case 1:
        return <Step2Marker onNext={handleNext} onBack={handleBack} />;
      case 2:
        return <Step3Videos onNext={handleNext} onBack={handleBack} />;
      case 3:
        return <Step4Schedule onNext={handleNext} onBack={handleBack} />;
      case 4:
        return <Step5QR onBack={handleBack} onFinish={handleFinish} />;
      default:
        return 'Unknown step';
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Создание AR-контента
        </Typography>
        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label, index) => (
            <Step key={index}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
        
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {getStepContent(activeStep)}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
              <Button
                disabled={activeStep === 0}
                onClick={handleBack}
                variant="outlined"
              >
                Назад
              </Button>
              <Button
                variant="contained"
                onClick={activeStep === steps.length - 1 ? handleFinish : handleNext}
                disabled={loading}
              >
                {activeStep === steps.length - 1 ? 'Завершить' : 'Далее'}
              </Button>
            </Box>
          </>
        )}
      </Paper>
    </Box>
  );
};

// pages/Projects/ARContent/ARContentWizard.tsx
import React from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  Button, 
  CircularProgress 
} from '@mui/material';
import { WizardProvider } from './useWizard';
import { WizardSteps } from './WizardSteps';

const ARContentWizard: React.FC<{ projectId: number }> = ({ projectId }) => {
  return (
    <WizardProvider projectId={projectId}>
      <Container maxWidth="lg">
        <WizardSteps />
      </Container>
    </WizardProvider>
  );
};

export default ARContentWizard;
