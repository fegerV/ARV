// components/(media)/Lightbox.tsx
import React from 'react';
import {
  Box,
  IconButton,
  Modal,
  Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

interface LightboxProps {
  open: boolean;
  onClose: () => void;
  type: 'image' | 'video';
  src: string;
  title?: string;
}

export const Lightbox: React.FC<LightboxProps> = ({ open, onClose, type, src, title }) => {
  return (
    <Modal
      open={open}
      onClose={onClose}
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Box
        sx={{
          position: 'relative',
          outline: 'none',
          maxHeight: '90vh',
          maxWidth: '90vw',
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 1300,
          }}
        >
          <IconButton
            onClick={onClose}
            sx={{
              bgcolor: 'background.paper',
              '&:hover': {
                bgcolor: 'background.paper',
                opacity: 0.8,
              },
            }}
          >
            <CloseIcon />
          </IconButton>
        </Box>

        {title && (
          <Box
            sx={{
              position: 'absolute',
              bottom: 8,
              left: 0,
              right: 0,
              textAlign: 'center',
              zIndex: 1300,
            }}
          >
            <Typography
              variant="h6"
              sx={{
                bgcolor: 'background.paper',
                display: 'inline-block',
                px: 2,
                py: 1,
                borderRadius: 1,
              }}
            >
              {title}
            </Typography>
          </Box>
        )}

        {type === 'image' ? (
          <Box
            component="img"
            src={src}
            alt={title}
            sx={{
              maxWidth: '100%',
              maxHeight: '80vh',
              objectFit: 'contain',
              borderRadius: 1,
            }}
          />
        ) : (
          <Box
            component="video"
            src={src}
            controls
            sx={{
              maxWidth: '100%',
              maxHeight: '80vh',
              borderRadius: 1,
            }}
          />
        )}
      </Box>
    </Modal>
  );
};