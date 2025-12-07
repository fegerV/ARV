// ARV/frontend/src/pages/projects/ProjectsList.tsx
import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Container,
  Paper,
  Typography,
  Chip,
  Button,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  MenuItem,
} from '@mui/material';
import { AppLayout } from '@/components/(layout)/AppLayout';
import { PageHeader } from '@/components/(layout)/PageHeader';
import { projectsApi } from '@/services/projects';

const ProjectsListPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const page = Number(searchParams.get('page') ?? 0);
  const limit = Number(searchParams.get('limit') ?? 25);
  const status = searchParams.get('status') ?? '';
  const search = searchParams.get('q') ?? '';

  const { data, isLoading } = useQuery(
    ['projects', { page, limit, status, search }],
    () =>
      projectsApi.list({
        page: page + 1,
        limit,
        status: status || undefined,
        search: search || undefined,
      })
  );

  const handlePageChange = (_: unknown, newPage: number) => {
    setSearchParams({
      page: String(newPage),
      limit: String(limit),
      status,
      q: search,
    });
  };

  const handleRowsPerPageChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newLimit = parseInt(event.target.value, 10);
    setSearchParams({
      page: '0',
      limit: String(newLimit),
      status,
      q: search,
    });
  };

  const projects = data?.data.projects ?? [];
  const total = data?.data.total ?? 0;

  return (
    <AppLayout>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <PageHeader
          title="Проекты"
          subtitle={`${total} проектов`}
          backUrl="/companies"
          actions={[
            {
              label: 'Новый проект',
              variant: 'contained',
              onClick: () => navigate('/projects/new'),
            },
          ]}
        />

        {/* Фильтры */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <TextField
              size="small"
              label="Поиск по названию"
              value={search}
              onChange={(e) =>
                setSearchParams({
                  page: '0',
                  limit: String(limit),
                  status,
                  q: e.target.value,
                })
              }
              sx={{ minWidth: 240 }}
            />
            <TextField
              select
              size="small"
              label="Статус"
              value={status}
              onChange={(e) =>
                setSearchParams({
                  page: '0',
                  limit: String(limit),
                  status: e.target.value,
                  q: search,
                })
              }
              sx={{ minWidth: 160 }}
            >
              <MenuItem value="">Все</MenuItem>
              <MenuItem value="active">Активные</MenuItem>
              <MenuItem value="paused">На паузе</MenuItem>
              <MenuItem value="archived">Архив</MenuItem>
            </TextField>
          </Box>
        </Paper>

        {/* Таблица проектов */}
        <Paper>
          {isLoading && <LinearProgress />}
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Название</TableCell>
                  <TableCell>Компания</TableCell>
                  <TableCell>Статус</TableCell>
                  <TableCell>AR‑заказы</TableCell>
                  <TableCell>Период</TableCell>
                  <TableCell align="right">Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {projects.length === 0 && !isLoading && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="text.secondary">
                        Проекты не найдены
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {projects.map((project: any) => (
                  <TableRow
                    key={project.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/projects/${project.id}/content`)}
                  >
                    <TableCell>
                      <Typography fontWeight={500}>{project.name}</Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >{`/${project.slug}`}</Typography>
                    </TableCell>
                    <TableCell>{project.company_name}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={project.status_human}
                        color={
                          project.status === 'active'
                            ? 'success'
                            : project.status === 'paused'
                            ? 'warning'
                            : 'default'
                        }
                      />
                    </TableCell>
                    <TableCell>
                      {project.ar_contents_count ?? 0}
                    </TableCell>
                    <TableCell>
                      {project.starts_at_readable} —{' '}
                      {project.expires_at_readable || 'без ограничений'}
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/projects/${project.id}/content/new`);
                        }}
                      >
                        Новый заказ
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={handlePageChange}
            rowsPerPage={limit}
            onRowsPerPageChange={handleRowsPerPageChange}
            rowsPerPageOptions={[10, 25, 50]}
          />
        </Paper>
      </Container>
    </AppLayout>
  );
};

export default ProjectsListPage;
