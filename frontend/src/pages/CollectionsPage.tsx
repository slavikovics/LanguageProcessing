import { useCallback, useEffect, useState } from "react";
import { deleteDocument, listDocuments } from "../api/client";
import type { DocumentSummary } from "../api/types";

import { CollectionHeaderCard } from "@/components/CollectionHeaderCard";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DocumentFormDialog } from "@/components/DocumentFormDialog";
import { DocumentsTable } from "@/components/DocumentsTable";
import { useCollectionContext } from "@/context/CollectionContext";

const PAGE_SIZE = 10;

type Dialog = { mode: "create"; document: null } | { mode: "edit"; document: DocumentSummary };

export function CollectionsPage() {
  const { selected, selectedId, refreshCollections } = useCollectionContext();
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [dialog, setDialog] = useState<Dialog | null>(null);

  const refreshDocuments = useCallback(async () => {
    if (selectedId === null) {
      setDocuments([]);
      return;
    }
    setLoading(true);
    try {
      setDocuments(await listDocuments(selectedId, { limit: PAGE_SIZE, offset: page * PAGE_SIZE }));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedId, page]);

  // Document counts can go stale if they changed elsewhere (a crawl job
  // finishing in another tab) — always re-check on arrival.
  useEffect(() => {
    void refreshCollections();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setPage(0);
    setDialog(null);
  }, [selectedId]);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  async function handleDelete(doc: DocumentSummary) {
    if (!window.confirm(`Удалить документ «${doc.title}»? Это действие необратимо.`)) return;
    setDeletingId(doc.id);
    try {
      await deleteDocument(doc.id);
      if (dialog?.document?.id === doc.id) setDialog(null);
      await Promise.all([refreshDocuments(), refreshCollections()]);
    } catch (err) {
      window.alert(err instanceof Error ? err.message : String(err));
    } finally {
      setDeletingId(null);
    }
  }

  if (selectedId === null || !selected) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Нет выбранной коллекции</CardTitle>
          <CardDescription>
            Создайте коллекцию через «+» у переключателя вверху страницы, или начните с краулинга —
            он предложит создать коллекцию автоматически.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const totalPages = Math.max(1, Math.ceil(selected.document_count / PAGE_SIZE));

  return (
    <div className="flex flex-col gap-6">
      <CollectionHeaderCard
        collection={selected}
        onDocumentsChanged={() => void refreshDocuments()}
        onAddDocument={() => setDialog({ mode: "create", document: null })}
      />

      <DocumentsTable
        documents={documents}
        loading={loading}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        onEdit={(doc) => setDialog({ mode: "edit", document: doc })}
        onDelete={handleDelete}
        deletingId={deletingId}
      />

      <DocumentFormDialog
        mode={dialog?.mode ?? "closed"}
        collectionId={selectedId}
        editingDocument={dialog?.document ?? null}
        onClose={() => setDialog(null)}
        onSaved={() => {
          void refreshDocuments();
          void refreshCollections();
        }}
      />
    </div>
  );
}
