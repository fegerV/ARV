// components/data/VirtualizedTableBodyUsageExample.tsx
// Пример использования VirtualizedTableBody в ARContentList

import React from 'react';
import { TableRow, TableCell, Typography } from '@mui/material';
import { VirtualizedTableBody } from './VirtualizedTableBody';

// Пример использования в ARContentList:
/*
// В DataTable компоненте, вместо tbody с map:
<tbody>
  {data.map((row, index) => (
    <TableRow key={row.id ?? index} hover onClick={() => onRowClick?.(row)}>
      {columns.map((column) => (
        <TableCell key={String(column.key)}>
          {column.render ? column.render(row[column.key], row) : row[column.key]}
        </TableCell>
      ))}
    </TableRow>
  ))}
</tbody>

// Используем VirtualizedTableBody:
<VirtualizedTableBody
  rows={data}
  rowHeight={64}
  height={600}
  renderRow={(row, index, style) => (
    <TableRow
      key={row.id ?? index}
      hover
      onClick={() => onRowClick?.(row)}
      style={style}
    >
      {columns.map((column) => (
        <TableCell key={String(column.key)}>
          {column.render ? column.render(row[column.key], row) : row[column.key]}
        </TableCell>
      ))}
    </TableRow>
  )}
/>
*/

// Это улучшение позволяет:
// 1. Виртуализировать таблицу для лучшей производительности при большом количестве строк
// 2. Рендерить только видимые строки, значительно улучшая производительность
// 3. Поддерживать все существующие функции таблицы (клик по строкам, рендер ячеек и т.д.)

export const VirtualizedTableBodyUsageExample = () => {
  return (
    <div>
      <Typography variant="h6" gutterBottom>
        Пример использования VirtualizedTableBody
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Этот компонент следует использовать в DataTable для виртуализации больших таблиц.
      </Typography>
    </div>
  );
};