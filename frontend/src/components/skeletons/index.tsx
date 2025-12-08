import { Box, Skeleton, Card, CardContent, Grid, Table, TableRow, TableCell, TableHead, TableBody } from '@mui/material';

/**
 * Скелетон для KPI карточки
 */
export function KpiSkeleton() {
  return (
    <Card>
      <CardContent>
        <Skeleton variant="text" width="60%" height={20} sx={{ mb: 1 }} />
        <Skeleton variant="text" width="100%" height={40} />
      </CardContent>
    </Card>
  );
}

/**
 * Скелетон для Recharts графика
 */
export function ChartSkeleton() {
  return (
    <Card>
      <CardContent>
        <Skeleton variant="text" width="50%" height={24} sx={{ mb: 2 }} />
        <Box sx={{ height: 300 }}>
          <Skeleton variant="rectangular" width="100%" height="100%" sx={{ borderRadius: 1 }} />
        </Box>
      </CardContent>
    </Card>
  );
}

/**
 * Скелетон для строки таблицы
 */
export function TableRowSkeleton({ columns = 6 }: { columns?: number }) {
  return (
    <TableRow>
      {Array.from({ length: columns }).map((_, idx) => (
        <TableCell key={idx}>
          <Skeleton variant="text" />
        </TableCell>
      ))}
    </TableRow>
  );
}

/**
 * Скелетон для таблицы
 */
export function TableSkeleton({ rows = 5, columns = 6 }: { rows?: number; columns?: number }) {
  return (
    <Table>
      <TableHead>
        <TableRowSkeleton columns={columns} />
      </TableHead>
      <TableBody>
        {Array.from({ length: rows }).map((_, idx) => (
          <TableRowSkeleton key={idx} columns={columns} />
        ))}
      </TableBody>
    </Table>
  );
}

/**
 * Скелетон для Dashboard
 */
export function DashboardSkeleton() {
  return (
    <Box>
      {/* KPI Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {Array.from({ length: 6 }).map((_, idx) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={idx}>
            <KpiSkeleton />
          </Grid>
        ))}
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        {Array.from({ length: 4 }).map((_, idx) => (
          <Grid item xs={12} md={6} key={idx}>
            <ChartSkeleton />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

/**
 * Скелетон для детальной страницы
 */
export function DetailPageSkeleton() {
  return (
    <Box>
      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Skeleton variant="text" width={400} height={40} />
      </Box>

      {/* Content */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Skeleton variant="text" width="40%" height={24} sx={{ mb: 2 }} />
              {Array.from({ length: 4 }).map((_, idx) => (
                <Skeleton key={idx} variant="text" sx={{ mb: 1 }} />
              ))}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Skeleton variant="text" width="40%" height={24} sx={{ mb: 2 }} />
              {Array.from({ length: 4 }).map((_, idx) => (
                <Skeleton key={idx} variant="text" sx={{ mb: 1 }} />
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
