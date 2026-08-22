import { useEffect, useState } from 'react'
import { downloadAssessmentExportDocx, previewAssessmentExportPdf } from '../../api/assessments'
import { ApiError, downloadBlob } from '../../api/client'
import Button from '../../components/ui/Button'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'

// Fetches the PDF once and shows the real generated file in an iframe (true
// WYSIWYG, not an HTML mirror). "Download PDF" reuses that same blob rather
// than re-requesting it, so what's previewed is guaranteed to match what's
// downloaded. Word export has no preview requirement -- direct download only.
export default function AssessmentExportModal({ isOpen, onClose, assessmentId, assessmentTitle }) {
  const [blob, setBlob] = useState(null)
  const [filename, setFilename] = useState('assessment.pdf')
  const [objectUrl, setObjectUrl] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isDownloadingDocx, setIsDownloadingDocx] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isOpen) return
    setError('')
    setIsLoading(true)
    ;(async () => {
      try {
        const result = await previewAssessmentExportPdf(assessmentId)
        setBlob(result.blob)
        setFilename(result.filename)
        setObjectUrl(URL.createObjectURL(result.blob))
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : 'Could not generate a preview.')
      } finally {
        setIsLoading(false)
      }
    })()

    return () => {
      setObjectUrl((current) => {
        if (current) URL.revokeObjectURL(current)
        return null
      })
      setBlob(null)
    }
  }, [isOpen, assessmentId])

  function handleDownloadPdf() {
    if (blob) downloadBlob(blob, filename)
  }

  async function handleDownloadDocx() {
    setError('')
    setIsDownloadingDocx(true)
    try {
      await downloadAssessmentExportDocx(assessmentId)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not download the Word document.')
    } finally {
      setIsDownloadingDocx(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      width="max-w-3xl"
      title={`Export — ${assessmentTitle}`}
      description="Review the exam paper before downloading."
    >
      {error && (
        <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : objectUrl ? (
        <iframe
          src={objectUrl}
          title="Assessment export preview"
          className="w-full rounded-lg border border-border"
          style={{ aspectRatio: '210 / 297', minHeight: '60vh' }}
        />
      ) : null}

      <ModalFooter>
        <Button type="button" variant="secondary" onClick={onClose}>
          Close
        </Button>
        <Button type="button" variant="secondary" onClick={handleDownloadDocx} isLoading={isDownloadingDocx}>
          Download Word
        </Button>
        <Button type="button" onClick={handleDownloadPdf} disabled={!blob}>
          Download PDF
        </Button>
      </ModalFooter>
    </Modal>
  )
}
