// components/(data)/ARContentRowActions.tsx
import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import { Eye, Edit, Trash2 } from 'lucide-react';

interface ARContentRowActionsProps {
  onPreview: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export const ARContentRowActions: React.FC<ARContentRowActionsProps> = ({
  onPreview,
  onEdit,
  onDelete
}) => {
  return (
    <>
      <Tooltip title="Просмотр">
        <IconButton size="small" onClick={(e) => {
          e.stopPropagation();
          onPreview();
        }}>
          <Eye size={18} />
        </IconButton>
      </Tooltip>
      
      <Tooltip title="Редактировать">
        <IconButton size="small" onClick={(e) => {
          e.stopPropagation();
          onEdit();
        }}>
          <Edit size={18} />
        </IconButton>
      </Tooltip>
      
      <Tooltip title="Удалить">
        <IconButton size="small" onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}>
          <Trash2 size={18} />
        </IconButton>
      </Tooltip>
    </>
  );
};