// Simple test to verify LazyImage component compiles correctly
import { LazyImage } from './LazyImage';

// This is a compile-time test to ensure the component is properly exported
export const testLazyImage = () => {
  return (
    <LazyImage
      src="test.jpg"
      alt="Test image"
      fallbackHeight={200}
    />
  );
};