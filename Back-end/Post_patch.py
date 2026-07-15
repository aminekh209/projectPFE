def normalize_type_params(
    data_type: Optional[str],
    type_params: Optional[str]
) -> str:
    data_type = (data_type or "").upper().strip()
    type_params = (type_params or "").replace(" ", "").upper()

    # Oracle représente TIMESTAMP comme TIMESTAMP(6)
    if data_type == "TIMESTAMP" and type_params in {"", "(6)"}:
        return ""

    # Oracle représente NUMBER(10) comme NUMBER(10,0)
    if data_type == "NUMBER":
        match = re.fullmatch(r"\((\d+),0\)", type_params)

        if match:
            return f"({match.group(1)})"

    return type_params






type_params = normalize_type_params(
    data_type=data_type,
    type_params=type_match.group(2) or ""
)