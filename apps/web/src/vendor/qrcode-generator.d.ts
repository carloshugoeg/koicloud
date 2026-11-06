/** Vendored qrcode-generator (Kazuhiko Arase, MIT). */
export default function qrcode(
  typeNumber: number,
  errorCorrectionLevel: "L" | "M" | "Q" | "H",
): {
  addData: (data: string, mode?: string) => void;
  make: () => void;
  getModuleCount: () => number;
  isDark: (row: number, col: number) => boolean;
  createSvgTag: (opts?: { cellSize?: number; margin?: number }) => string;
};
