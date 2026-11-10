import { useMemo } from "react";
import qrcode from "@/vendor/qrcode-generator";

type InviteAgentQrProps = {
  url: string;
};

export function InviteAgentQr({ url }: InviteAgentQrProps) {
  const svg = useMemo(() => {
    const qr = qrcode(0, "M");
    qr.addData(url);
    qr.make();
    return qr.createSvgTag({ cellSize: 4, margin: 2 });
  }, [url]);

  return (
    <div
      className="inline-block rounded-sm border border-line bg-paper p-2"
      data-testid="invite-agent-qr"
      data-invite-url={url}
      aria-label={`Código QR del enlace ${url}`}
      // SVG from the vendored generator is a fixed string for this url.
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
