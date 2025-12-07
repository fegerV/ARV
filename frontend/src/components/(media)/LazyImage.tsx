// components/media/LazyImage.tsx
import React from 'react';

type LazyImageProps = React.ImgHTMLAttributes<HTMLImageElement> & {
  fallbackHeight?: number;
};

export const LazyImage: React.FC<LazyImageProps> = ({
  src,
  alt,
  fallbackHeight = 120,
  ...rest
}) => {
  const ref = React.useRef<HTMLImageElement | null>(null);
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setVisible(true);
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: '200px 0px' } // подгружаем заранее
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <img
      ref={ref}
      src={visible ? (src as string) : undefined}
      data-src={src}
      alt={alt}
      loading="lazy"
      style={{ display: 'block', minHeight: fallbackHeight }}
      {...rest}
    />
  );
};