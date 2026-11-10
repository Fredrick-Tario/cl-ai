# Opt-in Git Bash integration for CL-AI Milestone 4.
# Load with: source <(cl-ai shell-init)

_cl_ai_is_own_command() {
    local command_text="$1"
    command_text="${command_text#"${command_text%%[![:space:]]*}"}"

    case "$command_text" in
        cl-ai|cl-ai\ *|command\ cl-ai|command\ cl-ai\ *) return 0 ;;
        *) return 1 ;;
    esac
}

_cl_ai_previous_command() {
    local offset candidate

    for ((offset = 1; offset <= 20; offset++)); do
        candidate="$(builtin fc -ln "-$offset" "-$offset" 2>/dev/null)" || continue
        # `fc -l` indents its display; remove that display-only prefix.
        candidate="${candidate#"${candidate%%[![:space:]]*}"}"

        [[ -z "${candidate//[[:space:]]/}" ]] && continue
        _cl_ai_is_own_command "$candidate" && continue

        printf '%s' "$candidate"
        return 0
    done

    return 1
}

_cl_ai_save_previous() {
    local candidate

    if ! candidate="$(_cl_ai_previous_command)"; then
        printf '%s\n' \
            'CL-AI could not read a previous Git Bash command; use the paste fallback.' \
            >&2
        command cl-ai save-last "$@"
        return $?
    fi

    printf '%s' "$candidate" | command cl-ai save-last --from-stdin "$@"
}

cl-ai() {
    if [[ "$1" == "save-last" ]]; then
        shift
        _cl_ai_save_previous "$@"
        return $?
    fi

    if [[ "$1" == "save" && "$2" == "the" && "$3" == "command" ]]; then
        shift 3
        _cl_ai_save_previous "$@"
        return $?
    fi

    command cl-ai "$@"
}
