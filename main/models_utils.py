"""General utilities for ProCat models."""


class Warning:
    """Warning mixin to collect possible model object issues."""

    @property
    def has_warnings(self) -> bool:
        """Flag that indicates if there are any warnings.

        It runs the `warnings` method and checks if it is empty or not.
        """
        # return True if self.warnings else False
        return bool(self.warnings)

    @property
    def warnings(self) -> list[str]:
        """List of warnings, created dynamically.

        It looks for class attributes which start with '_warn_', runs them, and
        appends either the string outlining the warning, or None if there is no warning
        flagged.
        """
        warnings_list = []

        # find all methods that start with "_warn_"
        for attr_name in dir(self):
            if attr_name.startswith("_warn_"):
                result = getattr(self, attr_name)()  # run the found function
                if result:
                    warnings_list.append(result)

        return warnings_list
