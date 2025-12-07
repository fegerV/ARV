// components/data/VirtualizedTableBody.tsx
import { FixedSizeList, ListChildComponentProps } from 'react-window';
import React from 'react';

interface VirtualizedTableBodyProps<T> {
  rows: T[];
  rowHeight: number;
  height: number;
  renderRow: (row: T, index: number, style: React.CSSProperties) => React.ReactNode;
}

export function VirtualizedTableBody<T>({
  rows,
  rowHeight,
  height,
  renderRow,
}: VirtualizedTableBodyProps<T>) {
  const Row = ({ index, style }: ListChildComponentProps) =>
    renderRow(rows[index], index, style);

  return (
    <FixedSizeList
      height={height}
      itemCount={rows.length}
      itemSize={rowHeight}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
}