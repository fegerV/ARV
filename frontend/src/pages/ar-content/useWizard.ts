// pages/Projects/ARContent/useWizard.ts
import React, { createContext, useContext, useState } from 'react';
import { VideoUpload, VideoRotationRule } from '../../types/ar-content';

interface WizardData {
  projectId: number;
  title: string;
  portraitFile: File | null;
  arContentId?: number;
  videos: VideoUpload[];
  rotationRule?: VideoRotationRule;
  unique_id?: string;
}

interface WizardContextType {
  data: WizardData;
  setData: React.Dispatch<React.SetStateAction<WizardData>>;
  currentStep: number;
  goNext: () => void;
  goBack: () => void;
  reset: () => void;
}

const WizardContext = createContext<WizardContextType | undefined>(undefined);

export const WizardProvider: React.FC<{ children: React.ReactNode; projectId: number }> = ({
  children,
  projectId
}) => {
  const [data, setData] = useState<WizardData>({
    projectId,
    title: '',
    portraitFile: null,
    videos: [],
    rotationRule: undefined
  });
  
  const [currentStep, setCurrentStep] = useState(0);

  const goNext = () => setCurrentStep(prev => Math.min(prev + 1, 5));
  const goBack = () => setCurrentStep(prev => Math.max(prev - 1, 0));
  const reset = () => {
    setData({ projectId, title: '', portraitFile: null, videos: [] });
    setCurrentStep(0);
  };

  return (
    <WizardContext.Provider value={{ data, setData, currentStep, goNext, goBack, reset }}>
      {children}
    </WizardContext.Provider>
  );
};

export const useWizard = () => {
  const context = useContext(WizardContext);
  if (!context) throw new Error('useWizard must be used within WizardProvider');
  return context;
};