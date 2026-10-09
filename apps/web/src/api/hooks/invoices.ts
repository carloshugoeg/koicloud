import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/lib/errors";

async function listInvoices() {
  const { data, error } = await apiClient.GET("/api/v1/invoices", {});
  if (error) {
    throw new ApiError(error);
  }

  return data?.invoices ?? [];
}

async function getInvoice(invoiceId: string) {
  const { data, error } = await apiClient.GET("/api/v1/invoices/{invoice_id}", {
    params: { path: { invoice_id: invoiceId } },
  });

  if (error || !data) {
    throw new ApiError(error);
  }

  return data;
}

export async function downloadInvoicePdf(invoiceId: string) {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/invoices/{invoice_id}/pdf",
    {
      params: { path: { invoice_id: invoiceId } },
      parseAs: "blob",
    },
  );

  if (error) {
    throw new ApiError(error);
  }

  if (!response.ok || data == null) {
    throw new ApiError({
      code: "internal_error",
      message: "No se pudo descargar la factura.",
      request_id: "unknown",
    });
  }

  return data instanceof Blob ? data : new Blob([data as BlobPart], { type: "application/pdf" });
}

export function useInvoicesQuery() {
  return useQuery({
    queryKey: ["invoices"],
    queryFn: listInvoices,
  });
}

export function useInvoiceQuery(invoiceId: string | undefined) {
  return useQuery({
    queryKey: ["invoices", invoiceId],
    queryFn: () => {
      if (!invoiceId) {
        throw new Error("invoiceId required when query is enabled");
      }
      return getInvoice(invoiceId);
    },
    enabled: Boolean(invoiceId),
  });
}
