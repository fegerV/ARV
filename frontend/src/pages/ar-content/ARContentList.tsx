import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Button,
  Chip,
  useTheme,
  IconButton
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus, Eye, Edit, Trash2 } from 'lucide-react';
import { useARContentList } from '../../hooks/useARContentList';
import { DataTable } from '../../components/(data)/DataTable';
import { ARContentFilters } from './ARContentFilters';
import { ContentPreviewCell } from '../../components/(media)/ContentPreviewCell';
import { MarkerStatusBadge } from '../../components/(media)/MarkerStatusBadge';
import { formatDate } from '../../utils/dateUtils';

const ARContentListPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { contents, total, pagination, isLoading, updatePagination } = useARContentList(Number(projectId));
  const navigate = useNavigate();

  const handleRowClick = (row: any) => {
    navigate(`/ar-content/${row.id}`);
  };

  const handlePreview = (id: number) => {
    navigate(`/ar-content/${id}`);
  };

  const handleEdit = (id: number) => {
    navigate(`/ar-content/${id}/edit`);
  };

  const handleDelete = (id: number) => {
    console.log('Delete content:', id);
  };

  const columns = [
    {
      key: 'preview',
      label: 'Портрет',
      width: '120px',
      render: (_: any, row: any) => (
        <ContentPreviewCell imageUrl={row.image_url || row.thumbnail_url} />
      )
    },
    {
      key: 'title',
      label: 'Название',
      width: '250px',
      render: (_: any, row: any) => (
        <Box>
          <Typography variant="body1" fontWeight={500}>
            {row.title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            ID: {row.unique_id.slice(0, 8)}...
          </Typography>
        </Box>
      )
    },
    {
      key: 'company_name',
      label: 'Компания',
      width: '180px',
      render: (company_name: string) => (
        <Chip label={company_name} size="small" variant="outlined" />
      )
    },
    {
      key: 'videos_count',
      label: 'Видео',
      width: '80px',
      render: (count: number) => (
        <Chip label={count} size="small" color="primary" />
      )
    },
    {
      key: 'marker_status',
      label: 'Маркер',
      width: '140px',
      render: (_: any, row: any) => (
        <MarkerStatusBadge status={row.marker_status} size="small" />
      )
    },
    {
      key: 'views',
      label: 'Просмотры',
      width: '100px',
      sortable: true,
      render: (views: number) => (
        <Typography variant="body2" fontWeight={500}>
          {views.toLocaleString()}
        </Typography>
      )
    },
    {
      key: 'created_at',
      label: 'Создан',
      width: '140px',
      sortable: true,
      render: (date: string) => formatDate(date)
    },
    {
      key: 'expires_at',
      label: 'Истекает',
      width: '140px',
      render: (date: string) => date ? formatDate(date) : '-'
    },
    {
      key: 'actions',
      label: 'Действия',
      width: '120px',
      render: (_: any, row: any) => (
        <Box sx={{ display: 'flex', gap: 1 }}>
          <IconButton 
            size="small" 
            onClick={(e) => {
              e.stopPropagation();
              handlePreview(row.id);
            }}
          >
            <Eye size={18} />
          </IconButton>
          <IconButton 
            size="small" 
            onClick={(e) => {
              e.stopPropagation();
              handleEdit(row.id);
            }}
          >
            <Edit size={18} />
          </IconButton>
          <IconButton 
            size="small" 
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(row.id);
            }}
          >
            <Trash2 size={18} />
          </IconButton>
        </Box>
      )
    }
  ];

  return (
    <Container maxWidth={false}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          AR Content ({total})
        </Typography>
        <Button
          variant="contained"
          startIcon={<Plus size={20} />}
          onClick={() => navigate(`/projects/${projectId}/content/new`)}
        >
          Создать AR Content
        </Button>
      </Box>

      <ARContentFilters />

      <DataTable
        data={contents}
        columns={columns}
        onRowClick={handleRowClick}
        loading={isLoading}
      />

      {/* Pagination would be implemented here in a real app */}
    </Container>
  );
};

export default ARContentListPage;
