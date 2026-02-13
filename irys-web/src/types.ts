export type RowValue = string | number | boolean | null;

export type TableRow = Record<string, RowValue>;

export interface ExportBatch {
  export_id: string;
  exported_at: string;
  row_count: number;
}

export interface ExtractResponse {
  table?: {
    headers?: string[];
    rows?: TableRow[];
  };
  rows?: TableRow[];
  headers?: string[];
  error?: string;
}

export interface ExportsListResponse {
  eventName?: string;
  exports?: ExportBatch[];
}

export interface ExportRowsResponse {
  eventName?: string;
  exportId?: string;
  rowCount?: number;
  rows?: TableRow[];
}
