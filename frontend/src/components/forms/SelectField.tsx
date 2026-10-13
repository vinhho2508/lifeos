import React from 'react'
import { Description, Label, ListBox, Select } from '@heroui/react'

interface SelectFieldProps {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
  description?: string
  placeholder?: string
}

/** Labeled single-select over a flat option list (thin wrapper over HeroUI Select). */
const SelectField: React.FC<SelectFieldProps> = ({
  label,
  value,
  options,
  onChange,
  description,
  placeholder = 'Select one',
}) => (
  <Select
    fullWidth
    placeholder={placeholder}
    value={value || null}
    onChange={(key) => key != null && onChange(String(key))}
  >
    <Label>{label}</Label>
    <Select.Trigger>
      <Select.Value />
      <Select.Indicator />
    </Select.Trigger>
    {description && <Description>{description}</Description>}
    <Select.Popover>
      <ListBox>
        {options.map((o) => (
          <ListBox.Item key={o.value} id={o.value} textValue={o.label}>
            {o.label}
            <ListBox.ItemIndicator />
          </ListBox.Item>
        ))}
      </ListBox>
    </Select.Popover>
  </Select>
)

export default SelectField
