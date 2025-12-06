// components/(data)/DataTable/DataTable.tsx
import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TableSortLabel,
  Box,
  Typography,
  CircularProgress
} from '@mui/material';

interface ColumnDef<T> {
  key: keyof T;
  label: string;
  width?: string;
  sortable?: boolean;
  render?: (value: any, row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  onRowClick?: (row: T) => void;
  loading?: boolean;
}

export const DataTable = <T extends Record<string, any>>({
  data,
  columns,
  onRowClick,
  loading
}: DataTableProps<T>) => {
  return (
    <TableContainer component={Paper} elevation={1}>
      <Table stickyHeader sx={{ minWidth: 1200 }}>
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell
                key={String(column.key)}
                sx={{
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  textTransform: 'uppercase',
                  letterSpacing: 0.5,
                  width: column.width
                }}
              >
                {column.sortable ? (
                  <TableSortLabel>{column.label}</TableSortLabel>
                ) : (
                  column.label
                )}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        
        <TableBody>
          {loading ? (
            <TableRow>
              <TableCell colSpan={columns.length} sx={{ py: 8, textAlign: 'center' }}>
                <CircularProgress />
              </TableCell>
            </TableRow>
          ) : data.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} sx={{ py: 12, textAlign: 'center' }}>
                <Typography color="text.secondary">
                  Нет заказов
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            data.map((row, index) => (
              <TableRow
                key={row.id || index}
                hover
                onClick={() => onRowClick?.(row)}
                sx={{ cursor: 'pointer' }}
              >
                {columns.map((column) => (
                  <TableCell key={String(column.key)}>
                    {column.render ? column.render(row[column.key], row) : row[column.key]}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
};