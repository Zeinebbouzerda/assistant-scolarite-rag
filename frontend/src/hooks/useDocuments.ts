import { useCallback, useEffect, useState } from "react";
import { api, describeError } from "../api/client";
import type { DocumentInfo } from "../api/types";

/**
 * Hook chargé de récupérer la liste des documents indexés via GET /api/documents
 * et d'en dériver la liste triée des types de documents disponibles pour les filtres.
 */
export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDocuments(await api.documents());
    } catch (e) {
      setError(describeError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const types = [...new Set(documents.map((d) => d.type))].sort();
  return { documents, types, loading, error, reload };
}
