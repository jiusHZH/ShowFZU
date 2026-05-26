import type { ChangeEvent } from 'react'

interface UploadPickerProps {
  accept: string
  actionText: string
  emptyText: string
  errorText?: string | null
  multiple?: boolean
  selectedItems: string[]
  onChange: (files: FileList | null) => void
  onRemove?: (index: number) => void
}

export function UploadPicker({
  accept,
  actionText,
  emptyText,
  errorText = null,
  multiple = false,
  selectedItems,
  onChange,
  onRemove,
}: UploadPickerProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.files)
    event.target.value = ''
  }

  return (
    <div className={errorText ? 'upload-picker has-error' : 'upload-picker'}>
      <div className="upload-picker__header">
        <span className="upload-picker__summary">{emptyText}</span>
        <label className="upload-picker__action">
          <input
            accept={accept}
            aria-label={actionText}
            className="upload-picker__input"
            multiple={multiple}
            type="file"
            onChange={handleChange}
          />
          <span aria-hidden="true" className="upload-picker__plus">+</span>
          <span>{actionText}</span>
        </label>
      </div>
      {selectedItems.length > 0 ? (
        <ul aria-label="Selected files" className="upload-picker__items">
          {selectedItems.map((item, index) => (
            <li className="upload-picker__item" key={`${item}-${index}`}>
              <span>{item}</span>
              {onRemove ? (
                <button aria-label={`Remove ${item}`} onClick={() => onRemove(index)} type="button">
                  Remove
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      {errorText ? (
        <p className="upload-picker__error" role="alert">
          <span aria-hidden="true" className="upload-picker__error-mark">!</span>
          <span>{errorText}</span>
        </p>
      ) : null}
    </div>
  )
}
