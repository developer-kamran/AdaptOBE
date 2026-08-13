import Input from '../../components/ui/Input'
import Textarea from '../../components/ui/Textarea'
import Select from '../../components/ui/Select'
import { OPTION_LABELS } from './questionTypes'

// Renders the type-specific fields for a single question item (the prompt
// text plus whatever `type_data` that type needs). Fully controlled so it
// can be reused inside both the single-item QuestionFormModal and each row
// of BulkQuestionModal.
export default function TypeFieldsEditor({ type, text, onTextChange, typeData, onTypeDataChange }) {
  function patchTypeData(patch) {
    onTypeDataChange({ ...typeData, ...patch })
  }

  if (type === 'mcq') {
    return (
      <div className="flex flex-col gap-3">
        <Textarea
          label="Question Text"
          rows={2}
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          required
        />
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-ink-700">Options</label>
          {OPTION_LABELS.map((label, index) => (
            <div key={label} className="flex items-center gap-2">
              <span className="w-5 text-xs font-semibold text-ink-500">{label}</span>
              <Input
                className="flex-1"
                placeholder={`Option ${label}`}
                value={typeData?.options?.[index]?.text ?? ''}
                onChange={(e) => {
                  const options = (typeData?.options ?? OPTION_LABELS.map((l) => ({ label: l, text: '' }))).map(
                    (opt, i) => (i === index ? { ...opt, text: e.target.value } : opt),
                  )
                  patchTypeData({ options })
                }}
                required
              />
            </div>
          ))}
        </div>
        <Select
          label="Correct Option"
          value={typeData?.correct_option ?? 'A'}
          onChange={(e) => patchTypeData({ correct_option: e.target.value })}
        >
          {OPTION_LABELS.map((label) => (
            <option key={label} value={label}>
              {label}
            </option>
          ))}
        </Select>
      </div>
    )
  }

  if (type === 'fill_blank') {
    return (
      <div className="flex flex-col gap-3">
        <Textarea
          label="Question Text (use ___ for the blank)"
          rows={2}
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          required
        />
        <Input
          label="Correct Answer"
          value={typeData?.answer ?? ''}
          onChange={(e) => patchTypeData({ answer: e.target.value })}
          required
        />
      </div>
    )
  }

  if (type === 'true_false') {
    return (
      <div className="flex flex-col gap-3">
        <Textarea
          label="Statement"
          rows={2}
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          required
        />
        <Select
          label="Correct Answer"
          value={typeData?.correct_answer ? 'true' : 'false'}
          onChange={(e) => patchTypeData({ correct_answer: e.target.value === 'true' })}
        >
          <option value="true">True</option>
          <option value="false">False</option>
        </Select>
      </div>
    )
  }

  if (type === 'project' || type === 'lab') {
    return (
      <div className="flex flex-col gap-3">
        <Input
          label="Title"
          placeholder={type === 'project' ? 'Semester Project' : 'Lab 3 — Database Normalization'}
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          required
        />
        <Textarea
          label={type === 'project' ? 'Description' : 'Description / Tasks'}
          rows={3}
          value={typeData?.description ?? ''}
          onChange={(e) => patchTypeData({ description: e.target.value })}
          required
        />
        {type === 'project' ? (
          <Input
            label="Deliverable (optional)"
            placeholder="Source code + report PDF"
            value={typeData?.deliverable ?? ''}
            onChange={(e) => patchTypeData({ deliverable: e.target.value })}
          />
        ) : (
          <Textarea
            label="Additional Tasks (optional)"
            rows={2}
            value={typeData?.tasks ?? ''}
            onChange={(e) => patchTypeData({ tasks: e.target.value })}
          />
        )}
      </div>
    )
  }

  // 'question' (regular)
  return (
    <Textarea
      label="Question Text"
      rows={2}
      value={text}
      onChange={(e) => onTextChange(e.target.value)}
      required
    />
  )
}
