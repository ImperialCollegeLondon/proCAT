"""General utilities for ProCat models."""


class Warning:
    """Warning mixin to collect possible model object issues."""

    @property
    def has_warnings(self) -> bool:
        """Flag that indicates if there are any warnings."""
        # return True if self.warnings else False
        return bool(self.warnings)

    @property
    def warnings(self) -> list[str]:
        """List of warnings, created dynamically."""
        warnings_list = []

        # find all methods that start with "_warn_"
        for attr_name in dir(self):
            if attr_name.startswith("_warn_"):
                result = getattr(self, attr_name)()
                if result:
                    warnings_list.append(result)

        return warnings_list
